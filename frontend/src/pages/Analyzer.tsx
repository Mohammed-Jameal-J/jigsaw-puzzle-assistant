import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import { usePuzzleAnalyzer } from "../hooks/usePuzzleAnalyzer";

const PHASE_LABELS = [
  "Reading photo",
  "Detecting pieces (contours, edges, tabs)",
  "Assigning piece IDs",
  "Classifying border & corner pieces",
  "Classifying tab / hole / flat edges",
  "Detecting piece orientation",
];

export default function Analyzer() {
  const { puzzleId } = useParams<{ puzzleId: string }>();
  const { summary, error } = usePuzzleAnalyzer(puzzleId);
  const navigate = useNavigate();

  useEffect(() => {
    if (summary?.status === "completed" && puzzleId) {
      navigate(`/results/${puzzleId}`);
    }
  }, [summary, puzzleId, navigate]);

  return (
    <Layout>
      <div className="card" style={{ maxWidth: 560, margin: "60px auto", textAlign: "center" }}>
        {error ? (
          <>
            <h2 style={{ color: "var(--error)", marginBottom: 10 }}>Detection failed</h2>
            <p style={{ color: "#6b7280" }}>{error}</p>
          </>
        ) : (
          <>
            <div
              aria-hidden="true"
              style={{
                width: 48,
                height: 48,
                margin: "0 auto 20px",
                border: "4px solid var(--border-color)",
                borderTopColor: "var(--secondary-blue)",
                borderRadius: "50%",
                animation: "spin 0.9s linear infinite",
              }}
            />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <h2 style={{ marginBottom: 16 }}>Analyzing your puzzle…</h2>
            <ul style={{ listStyle: "none", textAlign: "left", display: "inline-block" }}>
              {PHASE_LABELS.map((label) => (
                <li key={label} style={{ color: "#4b5563", padding: "4px 0", fontSize: 14 }}>
                  • {label}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </Layout>
  );
}
