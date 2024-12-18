# from fastapi import FastAPI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import Counter
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
from configparser import ConfigParser
import os
import spotipy
import webbrowser
import requests
from spotipy.oauth2 import SpotifyOAuth
import uvicorn

# FastAPI app setup
app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_methods=["*"],
    allow_headers=["*"],
)


GENIUS_ACCESS_TOKEN = 
SPOTIFY_CLIENT_ID = 
SPOTIFY_CLIENT_SECRET = 
REDIRECT_URI = "http://localhost:8000/callback"

HEADERS = {"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"}

# Spotify OAuth setup
scope = "user-top-read"
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope
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

# Endpoint to get top songs and fetch word frequencies
@app.get("/api/top-songs")
def get_top_songs():
    results = sp.current_user_top_tracks(limit=50, time_range="medium_term")
    songs = [{"title": track["name"], "artist": track["artists"][0]["name"]} for track in results["items"]]
    return {"songs": songs}

@app.post("/api/word-frequencies")
def get_word_frequencies():
    word_count = Counter()

    # Fetch top songs
    top_songs = [
        {"title": track["name"], "artist": track["artists"][0]["name"]}
        for track in sp.current_user_top_tracks(limit=50, time_range="medium_term")["items"]
    ]

    def filter_stopwords(lyrics):
        stop_words = set(stopwords.words('english'))
        filtered_words = [
            word.lower().strip(".,!?\"'()[]") 
            for word in lyrics.split() 
            if word.lower().strip(".,!?\"'()[]") not in stop_words
        ]
        return filtered_words


    # Generate the word frequency map
    for song in top_songs:
        try:
            lyrics = search_lyrics(song["title"], song["artist"])
            if lyrics:
                filtered_words = filter_stopwords(lyrics)
                word_count.update(filtered_words)
                print(f"Processed: {song['title']} by {song['artist']}")
            else:
                print(f"Lyrics not found for: {song['title']} by {song['artist']}")
        except Exception as e:
            print(f"Error processing {song['title']} by {song['artist']}: {e}")

    # Print the top 10 words
    print("\nTop 10 Words in the Word Map:")
    for word, freq in word_count.most_common(10):
        print(f"{word}: {freq}")

    return JSONResponse({"top_words": word_count.most_common(50)})

# Default root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Lyricalize API! Use the /api endpoints to interact."}

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
        redirect_url = f"http://localhost:3000/loading?access_token={access_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        print(f"Error during callback: {e}")
        return {"error": "Authentication failed"}
    

@app.get("/api/login")
def spotify_login():
    # Generate Spotify authorization URL
    auth_url = sp_oauth.get_authorize_url()
    return {"auth_url": auth_url}


if __name__ == "__main__":
    print("Please log in to Spotify...")

    # Spotify OAuth login
    auth_url = sp_oauth.get_authorize_url()
    print(f"Opening the following URL in your browser: {auth_url}")
    webbrowser.open(auth_url)

    # Start the server
    print("\nStarting the backend server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)

