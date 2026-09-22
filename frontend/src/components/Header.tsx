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
          <span style={{ fontSize: 26 }} aria-hidden="true">
            🧩
          </span>
          <span style={{ color: "#fff", fontWeight: 600, fontSize: 20 }}>
            Jigsaw Puzzle Assistant
          </span>
        </div>
      </Link>
    </header>
  );
}
