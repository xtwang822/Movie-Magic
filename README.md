# Movie-Magic

**Movie Magic** is a full-stack web application for movie lovers. Users can browse popular movies, view detailed information (like cast, crew, and trailers), and save favorites to their profile — all backed by Firebase Authentication and The Movie Database (TMDb) API.

---

## Features

- Movie and TV Show Search: Enable users to search for movies and TV shows by title, genre, or release date. 
- Detailed Information: Display detailed information for each movie or TV show, including summaries, ratings, cast, crew, and trailers. 
- User Reviews: Allow users to write and submit their own reviews for movies and TV shows. 
- User Accounts: Enable users to create accounts to save favorite articles, set alert preferences, and manage their profiles. Use Firebase for authentication. 
- Trending Content: Provide sections for trending movies, popular shows, and upcoming releases. 
- Favorites List: Users can create and manage a favorites list to save movies and shows they want to revisit.


---

## Tech Stack

| Frontend       | Backend      | Database | Auth        | External API |
|----------------|--------------|----------|-------------|---------------|
| HTML, CSS, JS  | Python (Flask) | SQLite   | Firebase Auth | [TMDb API](https://www.themoviedb.org/documentation/api) |

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/movie-magic.git
cd movie-magic
```

###  2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\\Scripts\\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

###  4. Add Your Configuration Files
```bash
Firebase Admin SDK
Add your firebase_admin_sdk.json file in the root directory.

Environment Variables
Create a .env file or set these in your shell:

FLASK_SECRET_KEY=your_flask_secret_key
TMDB_API_KEY=your_tmdb_api_key
FIREBASE_API_KEY=your_firebase_client_key
FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_STORAGE_BUCKET=your_project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your_sender_id
FIREBASE_APP_ID=your_app_id
```

## 5. Run the App
```bash
python app.py
```
Navigate to http://127.0.0.1:5000 in your browser.

## Database Schema
Tables:
movies — contains movie metadata
favorites — tracks user favorites (by Firebase UID + movie ID)
users — contains users

You can initialize the database with your own script or seed manually.

## Authentication
Authentication is handled entirely via Firebase. ID tokens are sent via Authorization headers to protect private routes like /profile, /favorite/<id>, etc.




