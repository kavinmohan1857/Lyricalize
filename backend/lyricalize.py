from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from collections import Counter
from pathlib import Path
from jose import JWTError, jwt
from uuid import uuid4
import os
import spotipy
import json
import requests
import asyncio
from spotipy.oauth2 import SpotifyOAuth
from bs4 import BeautifulSoup
import nltk

# Ensure stopwords are available
if not os.path.exists(os.path.join("nltk_data", "corpora", "stopwords")):
    nltk.download("stopwords")
from nltk.corpus import stopwords

# FastAPI app setup
app = FastAPI()

# CORS Setup
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,https://https://lyricalize-419bc3d24ee4.herokuapp.com/").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve React static files
app.mount("/static", StaticFiles(directory="build/static"), name="static")

# Environment variables
GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = "HS256"
HEADERS = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}

if not all([GENIUS_ACCESS_TOKEN, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, REDIRECT_URI]):
    raise RuntimeError("Missing required environment variables.")

# In-memory token store (replace with persistent storage for production)
token_store = {}

# Utility: Generate JWT Token
def create_jwt(data: dict, expires_in: int = 3600):
    from datetime import datetime, timedelta

    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(seconds=expires_in)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Utility: Decode JWT Token
def decode_jwt(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Spotify OAuth setup (per user session)
def get_spotify_oauth(user_id: str):
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-top-read",
        cache_path=f".spotify_cache_{user_id}"
    )

# Utility: Refresh Spotify Token
def refresh_spotify_token(user_id: str):
    sp_oauth = get_spotify_oauth(user_id)
    token_info = token_store.get(user_id)

    if not token_info:
        print(f"No token found for user {user_id}.")
        raise HTTPException(status_code=401, detail="Spotify token missing. Please log in.")

    if sp_oauth.is_token_expired(token_info):
        print(f"Token expired for user {user_id}. Refreshing token...")
        if "refresh_token" not in token_info:
            raise HTTPException(status_code=401, detail="No refresh token available. Please log in.")
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        token_store[user_id] = token_info
        print(f"Token refreshed for user {user_id}: {token_info}")
    else:
        print(f"Token is valid for user {user_id}.")

    return token_info

# Utility: Get Spotify Client
def get_spotify_client(user_id: str):
    token_info = refresh_spotify_token(user_id)
    return spotipy.Spotify(auth=token_info["access_token"])

def search_lyrics(title, artist):
    search_query = f"{title} {artist}"
    print(f"Searching for lyrics: Title='{title}', Artist='{artist}', Query='{search_query}'")
    
    response = requests.get(
        "https://api.genius.com/search",
        headers=HEADERS,
        params={"q": search_query},
    )

    print(f"Genius API Response Code: {response.status_code}")
    if response.status_code != 200:
        print(f"Genius API Error: {response.text}")
        return None

    hits = response.json().get("response", {}).get("hits", [])
    print(f"Genius API Hits: {len(hits)} found for query '{search_query}'")

    for hit in hits:
        print(f"Checking hit: {hit}")
        if artist.lower() in hit["result"]["primary_artist"]["name"].lower():
            song_url = hit["result"]["url"]
            print(f"Found matching lyrics URL: {song_url}")
            return scrape_lyrics(song_url)

    print("No matching lyrics found.")
    return None


# Utility: Scrape Lyrics
def scrape_lyrics(song_url):
    print(f"Scraping lyrics from URL: {song_url}")
    try:
        response = requests.get(song_url)
        print(f"Lyrics Page Response Code: {response.status_code}")
        if response.status_code != 200:
            print(f"Lyrics Page Error: {response.text}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        lyrics_containers = soup.select('div[data-lyrics-container="true"]')
        if not lyrics_containers:
            print("No lyrics containers found on the page.")
            return None

        lyrics = "\n".join([container.get_text() for container in lyrics_containers])
        print(f"Lyrics scraped successfully: {lyrics[:100]}...")  # Only print first 100 characters
        return lyrics
    except Exception as e:
        print(f"Error scraping lyrics: {e}")
    return None

# Utility: Filter Stopwords
def filter_stopwords(lyrics):
    stop_words = set(stopwords.words("english"))
    return [
        word.lower().strip(".,!?\"'()[]")
        for word in lyrics.split()
        if word.lower().strip(".,!?\"'()[]") not in stop_words
    ]

# Endpoint: Spotify Login
@app.get("/api/login")
def spotify_login():
    user_id = str(uuid4())
    token = create_jwt({"user_id": user_id})

    sp_oauth = get_spotify_oauth(user_id)
    auth_url = sp_oauth.get_authorize_url()

    return {"auth_url": f"{auth_url}&state={token}", "token": token}

# Spotify Callback Endpoint
@app.get("/callback")
def callback(code: str = None, state: str = None):
    if not code or not state:
        raise HTTPException(status_code=422, detail="Missing 'code' or 'state' query parameter")

    try:
        user = decode_jwt(state)
        user_id = user["user_id"]

        sp_oauth = get_spotify_oauth(user_id)
        token_info = sp_oauth.get_access_token(code, as_dict=True)

        # Save token info in the token_store
        if token_info:
            token_store[user_id] = token_info
            print(f"Token saved for user {user_id}: {token_info}")
        else:
            raise HTTPException(status_code=500, detail="Failed to retrieve Spotify token.")

        return RedirectResponse(url="https://lyricalize-419bc3d24ee4.herokuapp.com/loadingpage")
    except Exception as e:
        print(f"Error in /callback: {e}")
        return JSONResponse(content={"error": f"Authentication failed: {str(e)}"}, status_code=500)

# Endpoint: Get Word Frequencies
@app.post("/api/word-frequencies")
async def get_word_frequencies(request: Request):
    print(f"Incoming Authorization Header: {request.headers.get('Authorization')}")
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")

    token = auth_header.split(" ")[1]
    user = decode_jwt(token)

    try:
        sp = get_spotify_client(user["user_id"])
        top_songs = [
            {"title": track["name"], "artist": track["artists"][0]["name"]}
            for track in sp.current_user_top_tracks(limit=50, time_range="medium_term")["items"]
        ]
        print(f"Fetched top {len(top_songs)} songs from Spotify.")

        async def word_stream():
            word_count = Counter()
            for idx, song in enumerate(top_songs, start=1):
                print(f"Processing song {idx}/{len(top_songs)}: {song}")
                try:
                    lyrics = search_lyrics(song["title"], song["artist"])
                    if lyrics:
                        filtered_words = filter_stopwords(lyrics)
                        word_count.update(filtered_words)
                        yield f"data: {json.dumps({'song': song['title'], 'artist': song['artist'], 'progress': idx, 'total': len(top_songs)})}\n\n"
                    else:
                        print(f"No lyrics found for song: {song}")
                        yield f"data: {json.dumps({'song': song['title'], 'artist': song['artist'], 'progress': idx, 'error': 'No lyrics'})}\n\n"
                    await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"Error processing song {song}: {e}")
                    yield f"data: {json.dumps({'song': song['title'], 'error': str(e)})}\n\n"

            yield f"data: {json.dumps({'status': 'complete', 'top_words': word_count.most_common(50)})}\n\n"

        return StreamingResponse(word_stream(), media_type="text/event-stream")
    except Exception as e:
        print(f"Error in /api/word-frequencies: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Catch-All Route
@app.get("/{full_path:path}")
def serve_react_catchall(full_path: str):
    if not full_path.startswith("api/"):
        index_file = Path("build/index.html")
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="React build/index.html not found.")
        return FileResponse(index_file)
    return {"error": f"Invalid path: {full_path}"}

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
