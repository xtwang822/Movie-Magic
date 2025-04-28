import os
import sqlite3

import firebase_admin
import requests
from firebase_admin import credentials, auth
from flask import Flask, render_template, request, g
from flask import jsonify

from datetime import datetime
from flask import redirect, url_for

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_fallback_key")

# Load Firebase Admin SDK
cred_path = os.path.join(os.path.dirname(__file__), "firebase_admin_sdk.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

tmdb_key = os.getenv("TMDB_API_KEY")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"


def verify_firebase_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print("Error verifying Firebase token:", e)
        return None


@app.before_request
def check_auth():
    """Check for Firebase Authentication token in Authorization Header."""
    g.user = None

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        id_token = auth_header.split(" ")[1]
        user_data = verify_firebase_token(id_token)
        if user_data:
            g.user = user_data


def get_db_connection():
    conn = sqlite3.connect("movies.db")
    conn.row_factory = sqlite3.Row
    return conn


def tmdb_get(endpoint, **params):
    params.update({"api_key": TMDB_API_KEY, "language": "en-US"})
    return requests.get(f"{TMDB_BASE_URL}/{endpoint}", params=params).json()


def search_tmdb(query, year=None, genre=None, page=1):
    if year or genre:
        return tmdb_get(
            "discover/movie",
            with_original_language="en",
            with_genres=genre,
            primary_release_year=year,
            sort_by="popularity.desc",
            page=page,
            query=query,
        )
    return tmdb_get("search/multi", query=query, page=page)


def upsert_basic(m, conn):
    """Store minimal movie/TV info so detail page never 404s."""
    conn.execute(
        """INSERT OR REPLACE INTO movies
           (id, title, overview, release_date, poster_path, media_type)
           VALUES (?,?,?,?,?,?)""",
        (
            m["id"],
            m.get("title") or m.get("name"),
            m.get("overview", ""),
            m.get("release_date") or m.get("first_air_date") or "",
            m.get("poster_path"),
            m.get("media_type", "movie"),
        ),
    )


@app.route("/firebase-config")
def firebase_config():
    config = {
        "apiKey": os.getenv("FIREBASE_API_KEY"),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
        "projectId": os.getenv("FIREBASE_PROJECT_ID"),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
        "appId": os.getenv("FIREBASE_APP_ID")
    }
    print(config)
    if not config["apiKey"]:
        return jsonify({"error": "Firebase config missing!"}), 500
    return jsonify(config)

def trim18(resp_json):
    """Return at most 18 items from TMDb response JSON."""
    return resp_json.get("results", [])[:18]


@app.route("/")
def index():
    popular, upcoming, top_rated = get_home_lists()

    all_resp = tmdb_get("trending/all/day", page=1)
    all_page = trim18(all_resp)  # ← slice to 18
    total_pages = all_resp.get("total_pages", 1)

    # warm SQLite cache
    conn = get_db_connection()
    for itm in popular + upcoming + top_rated + all_page:
        upsert_basic(itm, conn)
    conn.commit();
    conn.close()

    return render_template(
        "index.html",
        popular=popular,
        upcoming=upcoming,
        top_rated=top_rated,
        all_page=all_page,
        page=1,
        total_pages=total_pages
    )


@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    conn = get_db_connection()
    movie = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()

    if movie is None:
        details_fresh = tmdb_get(f"movie/{movie_id}")
        if details_fresh.get("status_code") == 34:
            return "Movie not found", 404

        upsert_basic(details_fresh, conn)
        conn.commit()
        movie = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()

    reviews = conn.execute("""
        SELECT r.rating, r.text, r.created_at, r.firebase_uid
        FROM reviews r
        WHERE r.movie_id = ?
        ORDER BY r.created_at DESC
    """, (movie_id,)).fetchall()
    conn.close()

    details_url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
    credits_url = f"{TMDB_BASE_URL}/movie/{movie_id}/credits?api_key={TMDB_API_KEY}&language=en-US"
    videos_url = f"{TMDB_BASE_URL}/movie/{movie_id}/videos?api_key={TMDB_API_KEY}&language=en-US"

    details_resp = requests.get(details_url).json()
    credits_resp = requests.get(credits_url).json()
    videos_resp = requests.get(videos_url).json()

    cast = credits_resp.get("cast", [])[:8]
    crew = credits_resp.get("crew", [])[:8]

    trailer_link = None
    for video in videos_resp.get("results", []):
        if video["site"] == "YouTube" and video["type"] == "Trailer":
            trailer_link = f"https://www.youtube.com/watch?v={video['key']}"
            break

    return render_template("movie_detail.html",
                           movie=movie,
                           details=details_resp,
                           cast=cast,
                           crew=crew,
                           trailer_link=trailer_link,
                           reviews=reviews)


@app.route("/profile")
def profile():
    if not g.user:
        return "You must be logged in to see your profile.", 401

    firebase_uid = g.user["uid"]
    conn = get_db_connection()
    favorites = conn.execute("""
        SELECT m.id, m.title, m.poster_path
        FROM favorites f
        JOIN movies m on m.id = f.movie_id
        WHERE f.firebase_uid = ?
    """, (firebase_uid,)).fetchall()
    conn.close()

    return render_template("profile.html", favorites=favorites, user=g.user)


@app.route("/favorite/<int:movie_id>", methods=["POST"])
def add_favorite(movie_id):
    if not g.user:
        return jsonify({"error": "Not authenticated"}), 401

    firebase_uid = g.user["uid"]
    conn = sqlite3.connect("movies.db")

    # Check if the movie exists
    movie_check = conn.execute("SELECT id FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if not movie_check:
        conn.close()
        return jsonify({"error": "Movie not found"}), 404

    try:
        conn.execute("INSERT INTO favorites (firebase_uid, movie_id) VALUES (?, ?)", (firebase_uid, movie_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

    return jsonify({"message": "Movie added to favorites!"}), 200


@app.route("/favorite/remove/<int:movie_id>", methods=["POST"])
def remove_favorite(movie_id):
    if not g.user:
        return jsonify({"error": "Not authenticated"}), 401

    firebase_uid = g.user["uid"]
    conn = get_db_connection()
    conn.execute("DELETE FROM favorites WHERE firebase_uid = ? AND movie_id = ?", (firebase_uid, movie_id))
    conn.commit()
    conn.close()

    return jsonify({"message": "Movie removed from favorites"}), 200


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    year = request.args.get("year")
    genre = request.args.get("genre")
    page = max(1, int(request.args.get("page", 1)))

    if not query:
        return redirect(url_for("index"))

    resp = search_tmdb(query, year, genre, page=page)
    results = resp.get("results", [])
    total_pages = resp.get("total_pages", 1)
    total_results = resp.get("total_results", len(results))

    conn = get_db_connection()
    for itm in results: upsert_basic(itm, conn)
    conn.commit();
    conn.close()

    return render_template(
        "search_results.html",
        query=query,
        results=results,
        page=page,
        total_pages=total_pages,
        total_results=total_results  # ← NEW
    )


@app.route("/review/<int:movie_id>", methods=["POST"])
def add_review(movie_id):
    if not g.user:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(force=True)
    rating = int(data.get("rating", 0))
    text = data.get("text", "").strip()

    if rating < 1 or rating > 10 or not text:
        return jsonify({"error": "Invalid review"}), 400

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO reviews (firebase_uid, movie_id, rating, text, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (g.user["uid"], movie_id, rating, text, datetime.utcnow()))
    conn.commit()
    conn.close()

    return jsonify({"message": "Review submitted!"}), 200


def get_home_lists():
    popular = tmdb_get("trending/all/day").get("results", [])[:20]
    upcoming = tmdb_get("movie/upcoming").get("results", [])[:20]
    top_rated = tmdb_get("movie/top_rated").get("results", [])[:20]
    return popular, upcoming, top_rated


@app.route("/movies/all")
def movies_all():
    page = max(1, int(request.args.get("page", 1)))

    resp = tmdb_get("trending/all/day", page=page)
    all_page = trim18(resp)  # ← slice to 18
    total_pages = resp.get("total_pages", 1)

    popular, upcoming, top_rated = get_home_lists()

    conn = get_db_connection()
    for itm in all_page + popular + upcoming + top_rated:
        upsert_basic(itm, conn)
    conn.commit();
    conn.close()

    return render_template(
        "index.html",
        popular=popular,
        upcoming=upcoming,
        top_rated=top_rated,
        all_page=all_page,
        page=page,
        total_pages=total_pages
    )


# Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
