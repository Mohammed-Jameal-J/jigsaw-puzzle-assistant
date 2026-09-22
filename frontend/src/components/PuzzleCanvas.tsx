import { useEffect, useRef, useState } from "react";
import type { PieceMetadata } from "../types/puzzle";

const CANVAS_DISPLAY_WIDTH = 900;
const MIN_DRAW_SIZE = 16; // px; keeps tiny pieces draggable/clickable at scale
const CLICK_DRAG_THRESHOLD = 4; // px moved before a pointerdown counts as a drag, not a click
const MAX_PIECES_ON_CANVAS = 300; // keeps drag/redraw smooth; grid view covers the rest

const CLASSIFICATION_COLORS: Record<string, string> = {
  corner: "#f59e0b",
  border: "#3b82f6",
  interior: "#9ca3af",
  unknown: "#d1d5db",
};

interface PiecePos {
  piece: PieceMetadata;
  x: number; // canvas-space, current (draggable)
  y: number;
  w: number;
  h: number;
  homeX: number; // canvas-space, original detected layout — for "Reset positions"
  homeY: number;
}

interface PuzzleCanvasProps {
  imageUrl: string;
  pieces: PieceMetadata[];
  onPieceClick?: (piece: PieceMetadata) => void;
}

export default function PuzzleCanvas({ imageUrl, pieces, onPieceClick }: PuzzleCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const layoutRef = useRef<PiecePos[]>([]);
  const [ready, setReady] = useState(false);
  const [canvasHeight, setCanvasHeight] = useState(600);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const dragState = useRef<{ piece: PiecePos; startX: number; startY: number; moved: boolean; offX: number; offY: number } | null>(null);

  // Build the piece layout once the shared image is loaded.
  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      imgRef.current = img;
      const scale = CANVAS_DISPLAY_WIDTH / img.width;
      const displayHeight = img.height * scale;
      setCanvasHeight(displayHeight);

      const shown = pieces.slice(0, MAX_PIECES_ON_CANVAS);
      layoutRef.current = shown.map((piece) => {
        const [bx, by, bw, bh] = piece.bbox;
        const w = Math.max(MIN_DRAW_SIZE, bw * scale);
        const h = Math.max(MIN_DRAW_SIZE, bh * scale);
        const x = bx * scale;
        const y = by * scale;
        return { piece, x, y, w, h, homeX: x, homeY: y };
      });
      setReady(true);
    };
    img.src = imageUrl;
  }, [imageUrl, pieces]);

  function draw() {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const img = imgRef.current;
    if (!canvas || !ctx || !img) return;

    ctx.fillStyle = "#f3f4f6";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (const p of layoutRef.current) {
      const [bx, by, bw, bh] = p.piece.bbox;
      ctx.drawImage(img, bx, by, bw, bh, p.x, p.y, p.w, p.h);
      const isSelected = p.piece.piece_id === selectedId;
      ctx.lineWidth = isSelected ? 3 : 1.5;
      ctx.strokeStyle = isSelected ? "#1e40af" : CLASSIFICATION_COLORS[p.piece.classification] ?? "#d1d5db";
      ctx.strokeRect(p.x, p.y, p.w, p.h);
    }
  }

  useEffect(() => {
    if (ready) draw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, selectedId]);

  function pieceAt(x: number, y: number): PiecePos | null {
    // topmost-drawn-last wins, so search back-to-front
    for (let i = layoutRef.current.length - 1; i >= 0; i--) {
      const p = layoutRef.current[i];
      if (x >= p.x && x <= p.x + p.w && y >= p.y && y <= p.y + p.h) return p;
    }
    return null;
  }

  function toCanvasCoords(e: React.PointerEvent<HTMLCanvasElement>): { x: number; y: number } {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function handlePointerDown(e: React.PointerEvent<HTMLCanvasElement>) {
    const { x, y } = toCanvasCoords(e);
    const hit = pieceAt(x, y);
    if (!hit) {
      setSelectedId(null);
      return;
    }
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    dragState.current = { piece: hit, startX: x, startY: y, moved: false, offX: x - hit.x, offY: y - hit.y };
  }

  function handlePointerMove(e: React.PointerEvent<HTMLCanvasElement>) {
    const drag = dragState.current;
    if (!drag) return;
    const { x, y } = toCanvasCoords(e);
    if (!drag.moved && Math.hypot(x - drag.startX, y - drag.startY) > CLICK_DRAG_THRESHOLD) {
      drag.moved = true;
    }
    if (drag.moved) {
      const canvas = canvasRef.current!;
      drag.piece.x = Math.min(Math.max(0, x - drag.offX), canvas.width - drag.piece.w);
      drag.piece.y = Math.min(Math.max(0, y - drag.offY), canvas.height - drag.piece.h);
      draw();
    }
  }

  function handlePointerUp() {
    const drag = dragState.current;
    if (!drag) return;
    if (!drag.moved) {
      setSelectedId(drag.piece.piece.piece_id);
      onPieceClick?.(drag.piece.piece);
    }
    dragState.current = null;
  }

  function resetPositions() {
    for (const p of layoutRef.current) {
      p.x = p.homeX;
      p.y = p.homeY;
    }
    draw();
  }

  const shownCount = Math.min(pieces.length, MAX_PIECES_ON_CANVAS);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <p style={{ fontSize: 13, color: "#6b7280" }}>
          Drag a piece to move it, click to inspect it, showing {shownCount} of {pieces.length} pieces.
        </p>
        <button className="btn btn-secondary" onClick={resetPositions} style={{ padding: "6px 14px", fontSize: 13 }}>
          Reset positions
        </button>
      </div>
      <canvas
        ref={canvasRef}
        width={CANVAS_DISPLAY_WIDTH}
        height={canvasHeight}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
        style={{
          width: "100%",
          height: "auto",
          borderRadius: 8,
          border: "1px solid var(--border-color)",
          touchAction: "none",
          cursor: "grab",
        }}
      />
    </div>
  );
}
