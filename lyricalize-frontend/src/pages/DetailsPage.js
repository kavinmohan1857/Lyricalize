import React from "react";

function DetailsPage() {
  return (
    <div style={{ textAlign: "center", marginTop: "20%" }}>
      <h2>About Lyricalize</h2>
      <p>
        Lyricalize is a tool that analyzes the lyrics of the songs you listen to
        on Spotify and generates a word frequency map. By connecting your Spotify
        account, we fetch your most listened-to songs, extract their lyrics, and
        calculate the most commonly used words. This helps you explore the themes
        and patterns in the music you love.
      </p>
      <p>
        Privacy is important!!! and we only use the data needed to perform
        the analysis.
      </p>
    </div>
  );
}

export default DetailsPage;
