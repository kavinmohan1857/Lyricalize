import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import LoadingPage from "./pages/LoadingPage";
import WordMapPage from "./pages/WordMapPage";
import Header from "./components/Header";

function App() {
  return (
    <Router>
      <Header />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/loading" element={<LoadingPage />} />
        <Route path="/wordmap" element={<WordMapPage />} />
      </Routes>
    </Router>
  );
}

export default App;
