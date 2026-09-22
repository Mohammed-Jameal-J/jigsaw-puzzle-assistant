import { useEffect, useState } from "react";
import { apiErrorMessage, getPiece } from "../services/api";
import type { PieceMetadata } from "../types/puzzle";

interface PieceInspectorProps {
  puzzleId: string;
  piece: PieceMetadata;
  onClose: () => void;
}

const EDGE_ICON: Record<string, string> = { tab: "▲", hole: "▼", flat: "▬", unknown: "?" };

function EdgeRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--light-gray)" }}>
      <span style={{ color: "#6b7280", fontSize: 13 }}>{label}</span>
      <span style={{ fontWeight: 600, fontSize: 13 }}>
        {EDGE_ICON[value] ?? "?"} {value}
      </span>
    </div>
  );
}

export default function PieceInspector({ puzzleId, piece, onClose }: PieceInspectorProps) {
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const detail = await getPiece(puzzleId, piece.piece_id);
        if (!cancelled) setImageB64(detail.piece_image_base64);
      } catch (err) {
        if (!cancelled) setError(apiErrorMessage(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [puzzleId, piece.piece_id]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`${piece.piece_id} details`}
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(17, 24, 39, 0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
        padding: 20,
      }}
    >
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 380, width: "100%" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h3>{piece.piece_id}</h3>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{ border: "none", background: "none", fontSize: 20, cursor: "pointer", color: "#6b7280" }}
          >
            ×
          </button>
        </div>

        <div
          style={{
            width: "100%",
            aspectRatio: "1",
            background: "var(--light-gray)",
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 16,
            overflow: "hidden",
          }}
        >
          {error ? (
            <span style={{ color: "var(--error)", fontSize: 13, padding: 12, textAlign: "center" }}>{error}</span>
          ) : imageB64 ? (
            <img
              src={`data:image/png;base64,${imageB64}`}
              alt={`${piece.piece_id} crop`}
              style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }}
            />
          ) : (
            <span style={{ color: "#9ca3af", fontSize: 13 }}>Loading…</span>
          )}
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <span
            style={{
              background: "var(--light-gray)",
              borderRadius: 999,
              padding: "4px 12px",
              fontSize: 13,
              fontWeight: 600,
              textTransform: "capitalize",
            }}
          >
            {piece.classification}
          </span>
          <span style={{ background: "var(--light-gray)", borderRadius: 999, padding: "4px 12px", fontSize: 13 }}>
            {Math.round(piece.rotation)}° rotation
          </span>
        </div>

        <div>
          <EdgeRow label="Top" value={piece.edges.top} />
          <EdgeRow label="Right" value={piece.edges.right} />
          <EdgeRow label="Bottom" value={piece.edges.bottom} />
          <EdgeRow label="Left" value={piece.edges.left} />
        </div>

        <p style={{ color: "#9ca3af", fontSize: 12, marginTop: 12 }}>
          bbox: [{piece.bbox.join(", ")}] · centroid: ({piece.centroid[0]}, {piece.centroid[1]})
        </p>
      </div>
    </div>
  );
}
