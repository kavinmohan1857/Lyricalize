import React, { useEffect, useState } from "react";
import API_URL from "../config";

function LoadingPage() {
  const [currentSong, setCurrentSong] = useState("Starting...");
  const [currentArtist, setCurrentArtist] = useState("");
  const [progress, setProgress] = useState(0);
  const [totalSongs, setTotalSongs] = useState(50);
  const [wordMap, setWordMap] = useState([]);
  const [isComplete, setIsComplete] = useState(false); // Track when processing is complete

  useEffect(() => {
    const eventSource = new EventSource(`${API_URL}/api/word-frequencies`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.status === "complete") {
        // When processing is complete, update the state with top words
        setWordMap(data.top_words);
        setIsComplete(true);
        eventSource.close();
      } else if (data.song) {
        // Update progress, current song, and artist
        setCurrentSong(data.song);
        setCurrentArtist(data.artist || "Unknown Artist"); // Handle missing artist
        setProgress(data.progress);
        setTotalSongs(data.total || 50);
      }
    };

    eventSource.onerror = (error) => {
      console.error("Error fetching word frequencies:", error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  if (isComplete) {
    // Render the list of top words when processing is complete
    return (
      <div style={{ textAlign: "center", marginTop: "20%" }}>
        <h2>Top Words from Your Spotify Songs</h2>
        <ul
          style={{
            listStyleType: "none",
            padding: 0,
            textAlign: "left",
            display: "inline-block",
          }}
        >
          {wordMap.map(([word, count], index) => (
            <li key={index} style={{ marginBottom: "10px" }}>
              <strong>{word}</strong>: {count}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  // Render progress bar and song info while processing
  return (
    <div style={{ textAlign: "center", marginTop: "20%" }}>
      <h2>Generating your Word Map...</h2>
      <p>
        Processing: {currentSong} by {currentArtist}
      </p>
      <p>
        {progress}/{totalSongs} songs processed
      </p>
      <div
        style={{
          margin: "20px auto",
          width: "80%",
          height: "20px",
          backgroundColor: "#ddd",
          borderRadius: "10px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${(progress / totalSongs) * 100}%`,
            height: "100%",
            backgroundColor: "#1db954",
            transition: "width 0.3s ease",
          }}
        ></div>
      </div>
    </div>
  );
}

export default LoadingPage;
