import React from "react";
import WordCloud from "react-wordcloud";

function WordMapPage() {
  const wordData = JSON.parse(localStorage.getItem("wordData")) || [];

  const words = wordData.map(([text, value]) => ({ text, value }));

  return (
    <div style={{ textAlign: "center", marginTop: "20px" }}>
      <h2>Your Spotify Lyrics Word Map</h2>
      <div style={{ width: "800px", height: "500px", margin: "0 auto" }}>
        <WordCloud words={words} />
      </div>
    </div>
  );
}

export default WordMapPage;
