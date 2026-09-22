import { BrowserRouter, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import Analyzer from "./pages/Analyzer";
import Results from "./pages/Results";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/analyzer/:puzzleId" element={<Analyzer />} />
        <Route path="/results/:puzzleId" element={<Results />} />
      </Routes>
    </BrowserRouter>
  );
}
