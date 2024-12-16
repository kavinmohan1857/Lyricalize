import './App.css';
import { useEffect } from 'react';
import { getLyricalData } from './api'; // Import your API call


function App() {
  useEffect(() => {
    const fetchData = async () => {
      const data = await getLyricalData();
      console.log(data);
    };

    fetchData();
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Lyricalize</h1>
        <p>Analyzing your top Spotify songs...</p>
      </header>
      <main>
        {/* Components to display data */}
      </main>
    </div>
  );
}

export default App;
