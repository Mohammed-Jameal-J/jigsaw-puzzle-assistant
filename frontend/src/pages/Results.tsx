import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import DebugPanel from "../components/DebugPanel";
import PieceThumbnailGrid from "../components/PieceThumbnailGrid";
import PuzzleCanvas from "../components/PuzzleCanvas";
import PieceInspector from "../components/PieceInspector";
import { apiErrorMessage, getDebug, getPieces, getPuzzle } from "../services/api";
import type { DebugResponse, PieceMetadata, PuzzleSummary } from "../types/puzzle";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card" style={{ textAlign: "center", padding: 18 }}>
      <div style={{ fontSize: 28, fontWeight: 700, color: "var(--primary-blue)" }}>{value}</div>
      <div style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>{label}</div>
    </div>
  );
}

export default function Results() {
  const { puzzleId } = useParams<{ puzzleId: string }>();
  const [summary, setSummary] = useState<PuzzleSummary | null>(null);
  const [pieces, setPieces] = useState<PieceMetadata[]>([]);
  const [debug, setDebug] = useState<DebugResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPiece, setSelectedPiece] = useState<PieceMetadata | null>(null);
  const [view, setView] = useState<"canvas" | "grid">("canvas");

  useEffect(() => {
    if (!puzzleId) return;
    (async () => {
      try {
        const [s, p, d] = await Promise.all([
          getPuzzle(puzzleId),
          getPieces(puzzleId),
          getDebug(puzzleId),
        ]);
        setSummary(s);
        setPieces(p);
        setDebug(d);
      } catch (err) {
        setError(apiErrorMessage(err));
      }
    })();
  }, [puzzleId]);

  if (error) {
    return (
      <Layout>
        <p style={{ color: "var(--error)", textAlign: "center" }}>{error}</p>
      </Layout>
    );
  }

  if (!summary || !puzzleId) {
    return (
      <Layout>
        <p style={{ color: "#fff", textAlign: "center" }}>Loading results…</p>
      </Layout>
    );
  }

  return (
    <Layout>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 20 }}>
        <h1 style={{ color: "#fff" }}>Detection results</h1>
        <Link to="/" style={{ color: "#fff", fontSize: 14, textDecoration: "underline" }}>
          Analyze another photo
        </Link>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        <StatCard label="Pieces detected" value={summary.pieces_count} />
        <StatCard
          label="Processing time"
          value={summary.processing_time_ms ? `${Math.round(summary.processing_time_ms)} ms` : "—"}
        />
        <StatCard label="Corners" value={summary.corner_count} />
        <StatCard label="Border pieces" value={summary.border_count} />
        <StatCard label="Interior pieces" value={summary.interior_count} />
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 14 }}>Debug views</h3>
        {debug && <DebugPanel debug={debug} />}
      </div>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h3>
            Detected pieces{" "}
            <span style={{ color: "#9ca3af", fontWeight: 400, fontSize: 14 }}>
              (border = blue, corner = amber, interior = gray)
            </span>
          </h3>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              className={view === "canvas" ? "btn btn-primary" : "btn btn-secondary"}
              style={{ padding: "6px 14px", fontSize: 13 }}
              onClick={() => setView("canvas")}
            >
              Canvas
            </button>
            <button
              className={view === "grid" ? "btn btn-primary" : "btn btn-secondary"}
              style={{ padding: "6px 14px", fontSize: 13 }}
              onClick={() => setView("grid")}
            >
              Grid
            </button>
          </div>
        </div>

        {view === "canvas" ? (
          <PuzzleCanvas
            imageUrl={`/api/puzzle/${puzzleId}/image`}
            pieces={pieces}
            onPieceClick={setSelectedPiece}
          />
        ) : (
          <PieceThumbnailGrid
            imageUrl={`/api/puzzle/${puzzleId}/image`}
            pieces={pieces}
            onPieceClick={setSelectedPiece}
          />
        )}
      </div>

      {selectedPiece && (
        <PieceInspector puzzleId={puzzleId} piece={selectedPiece} onClose={() => setSelectedPiece(null)} />
      )}
    </Layout>
  );
}
