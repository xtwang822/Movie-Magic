import sqlite3
import requests
import os

# Load API key from environment variables
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

def create_tables():
    conn = sqlite3.connect("movies.db")
    c = conn.cursor()

    # Movies table
    c.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY,
            title TEXT,
            overview TEXT,
            release_date TEXT,
            poster_path TEXT
        )
    """)

    # Favorites table: references a movie's id and a user's Firebase UID
    c.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firebase_uid TEXT NOT NULL,
            movie_id INTEGER NOT NULL,
            UNIQUE(firebase_uid, movie_id)
        )
    """)

    conn.commit()
    conn.close()

def fetch_and_store_popular_movies():
    conn = sqlite3.connect("movies.db")
    c = conn.cursor()

    # For simplicity, we fetch only the first page of popular movies from TMDb
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
    response = requests.get(url)
    data = response.json()

    results = data.get("results", [])
    for movie in results:
        movie_id = movie["id"]
        title = movie["title"]
        overview = movie["overview"]
        release_date = movie["release_date"]
        poster_path = movie["poster_path"]  # e.g. "/path.jpg"

        # Insert or ignore if already exists
        c.execute("""
            INSERT OR IGNORE INTO movies (id, title, overview, release_date, poster_path)
            VALUES (?, ?, ?, ?, ?)
        """, (movie_id, title, overview, release_date, poster_path))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
    fetch_and_store_popular_movies()
    print("Database initialized and populated with TMDb popular movies!")
