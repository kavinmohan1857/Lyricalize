import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API_URL from "../config";

function LoadingPage() {
  const [currentSong, setCurrentSong] = useState("Starting...");
  const [progress, setProgress] = useState(0);
  const [totalSongs, setTotalSongs] = useState(50);
  const [wordMap, setWordMap] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const eventSource = new EventSource(`${API_URL}/api/word-frequencies`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.status === "complete") {
        // Update word map and stop streaming
        setWordMap(data.top_words);
        eventSource.close();
      } else if (data.song) {
        // Update progress and current song
        setCurrentSong(data.song);
        setProgress(data.progress);
        setTotalSongs(data.total || 50);
      }
    };

    eventSource.onerror = (error) => {
      console.error("Error fetching word frequencies:", error);
      eventSource.close();
    };

    return () => eventSource.close();
  }, []);

  return (
    <div style={{ textAlign: "center", marginTop: "20%" }}>
      <h2>Generating your Word Map...</h2>
      {wordMap.length > 0 ? (
        <div>
          <h3>Top 100 Words:</h3>
          <ul style={{ textAlign: "left", margin: "0 auto", width: "50%" }}>
            {wordMap.map(([word, frequency], index) => (
              <li key={index}>
                {word}: {frequency}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div>
          <p>Processing: {currentSong}</p>
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
      )}
    </div>
  );
}

export default LoadingPage;
