import { useEffect, useRef, useState } from "react";
import type { PieceMetadata } from "../types/puzzle";
import PieceThumb from "./PieceThumb";

const DEFAULT_VISIBLE = 200;

interface PieceThumbnailGridProps {
  imageUrl: string;
  pieces: PieceMetadata[];
  onPieceClick?: (piece: PieceMetadata) => void;
}

export default function PieceThumbnailGrid({ imageUrl, pieces, onPieceClick }: PieceThumbnailGridProps) {
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [visibleCount, setVisibleCount] = useState(DEFAULT_VISIBLE);

  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      imgRef.current = img;
      setLoaded(true);
    };
    img.src = imageUrl;
  }, [imageUrl]);

  if (!loaded || !imgRef.current) {
    return <p style={{ color: "#6b7280" }}>Loading piece previews…</p>;
  }

  const visible = pieces.slice(0, visibleCount);

  return (
    <div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(68px, 1fr))",
          gap: 8,
        }}
      >
        {visible.map((piece) => (
          <PieceThumb
            key={piece.piece_id}
            piece={piece}
            image={imgRef.current!}
            onClick={onPieceClick ? () => onPieceClick(piece) : undefined}
          />
        ))}
      </div>
      {visibleCount < pieces.length && (
        <div style={{ textAlign: "center", marginTop: 16 }}>
          <button
            className="btn btn-secondary"
            onClick={() => setVisibleCount((c) => c + 400)}
          >
            Show more ({pieces.length - visibleCount} remaining)
          </button>
        </div>
      )}
    </div>
  );
}
