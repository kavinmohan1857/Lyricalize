# from fastapi import FastAPI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from collections import Counter
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
import os
import spotipy
import webbrowser
import requests
from spotipy.oauth2 import SpotifyOAuth
import uvicorn

# FastAPI app setup
app = FastAPI()

# Serve React static files
app.mount("/static", StaticFiles(directory="build/static"), name="static")

@app.get("/")
def serve_react():
    return FileResponse("build/index.html")

# CORS Setup
origins = [
    "http://localhost:3000",  # For local testing
    "https://lyricalize-419bc3d24ee4.herokuapp.com"  # Deployed frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Access env variables
GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")  # Default to local callback for testing

HEADERS = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}

# Spotify OAuth setup
scope = "user-top-read"
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope,
    cache_path=".spotify_cache"  # Cache the token locally
)




# Function to search for lyrics using Genius API
def search_lyrics(title, artist):
    search_query = f"{title} {artist}"
    response = requests.get(
        "https://api.genius.com/search",
        headers=HEADERS,
        params={"q": search_query}
    )
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None

    hits = response.json()["response"]["hits"]
    for hit in hits:
        if artist.lower() in hit["result"]["primary_artist"]["name"].lower():
            song_url = hit["result"]["url"]
            lyrics = scrape_lyrics(song_url)
            return lyrics
    return None

# Function to scrape lyrics from a Genius song URL
from bs4 import BeautifulSoup

def scrape_lyrics(song_url):
    try:
        response = requests.get(song_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            lyrics_div = soup.find("div", class_="lyrics")
            if lyrics_div:
                return lyrics_div.get_text()
            else:
                # New Genius page format
                lyrics_containers = soup.select('div[data-lyrics-container="true"]')
                lyrics = "\n".join([container.get_text() for container in lyrics_containers])
                return lyrics
    except Exception as e:
        print(f"Error scraping lyrics from {song_url}: {e}")
    return None

# Create a function to get a valid token
def get_spotify_client():
    token_info = sp_oauth.get_cached_token()
    if not token_info or sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    return spotipy.Spotify(auth=token_info['access_token'])

# Endpoint to get top songs and fetch word frequencies
@app.get("/api/top-songs")
def get_top_songs():
    sp = get_spotify_client()
    results = sp.current_user_top_tracks(limit=50, time_range="medium_term")
    songs = [{"title": track["name"], "artist": track["artists"][0]["name"]} for track in results["items"]]
    return {"songs": songs}

@app.post("/api/word-frequencies")
def get_word_frequencies():
    from fastapi.responses import StreamingResponse
import json

@app.post("/api/word-frequencies")
async def get_word_frequencies():
    sp = get_spotify_client()
    top_songs = [
        {"title": track["name"], "artist": track["artists"][0]["name"]}
        for track in sp.current_user_top_tracks(limit=50, time_range="medium_term")["items"]
    ]
    async def filter_stopwords(lyrics):
            stop_words = set(stopwords.words('english'))
            filtered_words = [
                word.lower().strip(".,!?\"'()[]") 
                for word in lyrics.split() 
                if word.lower().strip(".,!?\"'()[]") not in stop_words
            ]
            return filtered_words

    async def word_stream():
        word_count = Counter()
        for idx, song in enumerate(top_songs, start=1):
            try:
                lyrics = search_lyrics(song["title"], song["artist"])
                if lyrics:
                    filtered_words = filter_stopwords(lyrics)
                    word_count.update(filtered_words)
                    yield f"data: {json.dumps({'song': song['title'], 'progress': idx, 'total': len(top_songs)})}\n\n"
                else:
                    yield f"data: {json.dumps({'song': song['title'], 'progress': idx, 'total': len(top_songs), 'error': 'No lyrics'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'song': song['title'], 'error': str(e)})}\n\n"

        yield f"data: {json.dumps({'status': 'complete', 'top_words': word_count.most_common(50)})}\n\n"

    return StreamingResponse(word_stream(), media_type="text/event-stream")


# Default root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Lyricalize API! Use the /api endpoints to interact."}

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Spotify OAuth callback
@app.get("/callback")
def callback(code: str):
    try:
        # Exchange the code for access token
        token_info = sp_oauth.get_access_token(code, as_dict=True)

        # Access token
        access_token = token_info['access_token']
        print("Login successful! Access token acquired.")

        # Redirect the user to the frontend with access_token as a query parameter
        redirect_url = f"{FRONTEND_URL}/loading?access_token={access_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        print(f"Error during callback: {e}")
        return {"error": "Authentication failed"}
    

@app.get("/api/login")
def spotify_login():
    # Generate Spotify authorization URL
    auth_url = sp_oauth.get_authorize_url()
    print(f"Generated Spotify Auth URL: {auth_url}")
    return {"auth_url": auth_url}
# Optional: Catch-all route to serve index.html for React Router
from fastapi.responses import RedirectResponse

@app.get("/{full_path:path}")
def serve_react_catchall(full_path: str):
    if full_path.startswith("api/"):
        return {"detail": "Not Found"}
    return FileResponse("build/index.html")


if __name__ == "__main__":
    print("Please log in to Spotify...")

    # Spotify OAuth login
    auth_url = sp_oauth.get_authorize_url()
    print(f"Opening the following URL in your browser: {auth_url}")
    webbrowser.open(auth_url)

    # Start the server
    print("\nStarting the backend server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)

