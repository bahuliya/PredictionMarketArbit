import React from "react";
import { Routes, Route, Link } from "react-router-dom";
import MarketList from "./pages/MarketList.jsx";
import MarketDetail from "./pages/MarketDetail.jsx";

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">Orderbooks</Link>
      </header>

      <main className="content">
        <Routes>
          <Route path="/" element={<MarketList />} />
          <Route path="/market/:ticker" element={<MarketDetail />} />
        </Routes>
      </main>
    </div>
  );
}
