import React, { useEffect, useState } from "react"; // Import React and hooks
import API_URL from "../config"; // Import API_URL from your config file

function LoadingPage() {
  const [currentSong, setCurrentSong] = useState("Starting...");
  const [currentArtist, setCurrentArtist] = useState("");
  const [progress, setProgress] = useState(0);
  const [totalSongs, setTotalSongs] = useState(50);
  const [wordMap, setWordMap] = useState([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState(null);

  // Verify and log the token saving process
  useEffect(() => {
    const checkAndSaveToken = () => {
      // Get token from query params if not in localStorage
      const queryParams = new URLSearchParams(window.location.search);
      const tokenFromURL = queryParams.get("token");

      if (tokenFromURL) {
        localStorage.setItem("jwt_token", tokenFromURL);
        console.log("JWT token extracted from URL and saved:", tokenFromURL);
      }

      const savedToken = localStorage.getItem("jwt_token");
      if (savedToken) {
        console.log("JWT token found in localStorage:", savedToken);
      } else {
        console.error("JWT token is missing. Redirecting to login...");
        setError("Authorization token is missing. Please log in again.");
      }
    };

    checkAndSaveToken();
  }, []);

  // Fetch word frequencies
  useEffect(() => {
    const fetchWordFrequencies = async () => {
      const token = localStorage.getItem("jwt_token");

      if (!token) {
        setError("Authorization token is missing. Please log in again.");
        return;
      }

      try {
        const response = await fetch(`${API_URL}/api/word-frequencies`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error("Unauthorized. Please log in again.");
          }
          throw new Error("Failed to fetch word frequencies.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split("\n\n");
          for (const event of events) {
            if (!event.trim()) continue;
            const data = JSON.parse(event.replace(/^data: /, ""));
            console.log("Received data:", data);

            if (data.status === "complete") {
              console.log("Processing complete:", data.top_words);
              setWordMap(data.top_words);
              setIsComplete(true);
              return;
            } else if (data.song) {
              setCurrentSong(data.song);
              setCurrentArtist(data.artist || "Unknown Artist");
              setProgress(data.progress);
              setTotalSongs(data.total || 50);
            }
          }
          buffer = buffer.slice(buffer.lastIndexOf("\n\n") + 2);
        }
      } catch (err) {
        console.error("Error fetching word frequencies:", err);
        setError(err.message || "An error occurred while generating your word map.");
      }
    };

    fetchWordFrequencies();
  }, []);

  if (error) {
    return (
      <div style={{ textAlign: "center", marginTop: "20%" }}>
        <h2>Error</h2>
        <p>{error}</p>
      </div>
    );
  }

  if (isComplete) {
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
          role="progressbar"
          aria-valuenow={(progress / totalSongs) * 100}
          aria-valuemin="0"
          aria-valuemax="100"
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
