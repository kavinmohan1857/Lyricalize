import React from "react";
import { useLocation } from "react-router-dom";

function WordMapPage() {
  const location = useLocation();
  const { data } = location.state || { data: [] };

  return (
    <div style={{ textAlign: "center", marginTop: "5%" }}>
      <h2>Your Word Map</h2>
      <ul style={{ listStyleType: "none", fontSize: "1.2em" }}>
        {data.length > 0 ? (
          data.map(([word, freq], index) => (
            <li key={index}>
              {word}: {freq}
            </li>
          ))
        ) : (
          <p>No word map data available.</p>
        )}
      </ul>
    </div>
  );
}

export default WordMapPage;
