import { useEffect, useRef } from "react";
import type { PieceMetadata } from "../types/puzzle";

const THUMB_SIZE = 64;

interface PieceThumbProps {
  piece: PieceMetadata;
  image: HTMLImageElement;
  onClick?: () => void;
}

const CLASSIFICATION_COLORS: Record<string, string> = {
  corner: "#f59e0b",
  border: "#3b82f6",
  interior: "#d1d5db",
  unknown: "#e5e7eb",
};

export default function PieceThumb({ piece, image, onClick }: PieceThumbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const [x, y, w, h] = piece.bbox;
    ctx.clearRect(0, 0, THUMB_SIZE, THUMB_SIZE);
    // letterbox the crop into a square thumbnail without distorting aspect ratio
    const scale = Math.min(THUMB_SIZE / w, THUMB_SIZE / h);
    const dw = w * scale;
    const dh = h * scale;
    const dx = (THUMB_SIZE - dw) / 2;
    const dy = (THUMB_SIZE - dh) / 2;
    ctx.drawImage(image, x, y, w, h, dx, dy, dw, dh);
  }, [piece, image]);

  return (
    <button
      onClick={onClick}
      title={`${piece.piece_id} · ${piece.classification}`}
      style={{
        border: `2px solid ${CLASSIFICATION_COLORS[piece.classification]}`,
        borderRadius: 6,
        padding: 0,
        width: THUMB_SIZE + 4,
        height: THUMB_SIZE + 4,
        background: "var(--light-gray)",
        cursor: onClick ? "pointer" : "default",
        overflow: "hidden",
      }}
    >
      <canvas ref={canvasRef} width={THUMB_SIZE} height={THUMB_SIZE} />
    </button>
  );
}
