import { Puzzle } from "lucide-react";
import { Link } from "react-router-dom";

export default function Header() {
  return (
    <header
      style={{
        padding: "20px 32px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <Link to="/" style={{ textDecoration: "none" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Puzzle size={26} color="white" aria-hidden="true" />
          <span style={{ color: "#fff", fontWeight: 600, fontSize: 20 }}>
            Jigsaw Puzzle Assistant
          </span>
        </div>
      </Link>
    </header>
  );
}
