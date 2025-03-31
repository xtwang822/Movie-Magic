import os
import sqlite3

# Firebase Admin imports
import firebase_admin
import requests
from firebase_admin import credentials, auth
from flask import Flask, render_template, request, jsonify, g

from flask import jsonify



app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_fallback_key")

# ✅ Load Firebase Admin SDK
cred_path = os.path.join(os.path.dirname(__file__), "firebase_admin_sdk.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

# ✅ TMDb API Configuration
tmdb_key = os.getenv("TMDB_API_KEY")

# ✅ Load API key from environment variables
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# ✅ Helper function to verify Firebase ID Token
def verify_firebase_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token  # Returns user data (UID, email, etc.)
    except Exception as e:
        print("Error verifying Firebase token:", e)
        return None

# ✅ Middleware to check user authentication
# @app.before_request
# def check_auth():
#     token = request.args.get("token")  # Get token from URL query
#     if token:
#         user_data = verify_firebase_token(token)
#         if user_data:
#             g.user = user_data  # Store user info in Flask's global `g`
#         else:
#             g.user = None  # Invalid token
#     else:
#         g.user = None  # No token provided

@app.before_request
def check_auth():
    """Check for Firebase Authentication token in Authorization Header."""
    g.user = None  # Default: No authenticated user

    auth_header = request.headers.get("Authorization")  # ✅ Get the token from headers
    if auth_header and auth_header.startswith("Bearer "):
        id_token = auth_header.split(" ")[1]  # Extract the token
        user_data = verify_firebase_token(id_token)
        if user_data:
            g.user = user_data  # Store user info in Flask's `g`


# ✅ Helper function to get DB connection
def get_db_connection():
    conn = sqlite3.connect("movies.db")
    conn.row_factory = sqlite3.Row
    return conn

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
    if not config["apiKey"]:
        return jsonify({"error": "Firebase config missing!"}), 500  # ✅ Log error if missing
    return jsonify(config)

# ✅ Home Route: List movies from the database
@app.route("/")
def index():
    conn = get_db_connection()
    movies = conn.execute("SELECT * FROM movies ORDER BY release_date DESC").fetchall()
    conn.close()
    return render_template("index.html", movies=movies)

# ✅ Movie Detail Route: Fetches movie details from TMDb in real-time
@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    conn = get_db_connection()
    movie = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    conn.close()
    if not movie:
        return "Movie not found", 404

    # Fetch additional details, cast, crew, and trailers from TMDb
    details_url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
    credits_url = f"{TMDB_BASE_URL}/movie/{movie_id}/credits?api_key={TMDB_API_KEY}&language=en-US"
    videos_url = f"{TMDB_BASE_URL}/movie/{movie_id}/videos?api_key={TMDB_API_KEY}&language=en-US"

    details_resp = requests.get(details_url).json()
    credits_resp = requests.get(credits_url).json()
    videos_resp = requests.get(videos_url).json()

    # Extract cast, crew, and trailer link
    cast = credits_resp.get("cast", [])[:8]  # First 8 cast members
    crew = credits_resp.get("crew", [])[:8]  # First 8 crew members
    trailer_link = None
    for video in videos_resp.get("results", []):
        if video["site"] == "YouTube" and video["type"] == "Trailer":
            trailer_link = f"https://www.youtube.com/watch?v={video['key']}"
            break

    return render_template("movie_detail.html", movie=movie, details=details_resp, cast=cast, crew=crew, trailer_link=trailer_link)

# ✅ Profile Route: Shows favorite movies for authenticated users
@app.route("/profile")
def profile():
    if not g.user:
        return "You must be logged in to see your profile.", 401  # ✅ Return 401 for unauthorized users

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

# ✅ Add Favorite Route: Allows users to save favorite movies
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
        pass  # User already favorited this movie
    finally:
        conn.close()

    return jsonify({"message": "Movie added to favorites!"}), 200

# ✅ Remove Favorite Route: Allows users to remove favorites
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

# ✅ Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
