// Mirrors backend/app/schemas/puzzle.py — keep these in sync by hand since
// the MVP has no shared-schema codegen step.

export type PuzzleStatus = "uploaded" | "processing" | "completed" | "failed";

export type EdgeType = "tab" | "hole" | "flat" | "unknown";

export type PieceClassification = "corner" | "border" | "interior" | "unknown";

export interface UploadResponse {
  puzzle_id: string;
  pieces_count: number;
  image_dims: [number, number];
  status: PuzzleStatus;
}

export interface PuzzleSummary {
  puzzle_id: string;
  status: PuzzleStatus;
  pieces_count: number;
  border_count: number;
  interior_count: number;
  corner_count: number;
  processing_time_ms: number | null;
  error: string | null;
}

export interface EdgeSignature {
  top: EdgeType;
  right: EdgeType;
  bottom: EdgeType;
  left: EdgeType;
}

export interface PieceMetadata {
  piece_id: string;
  bbox: [number, number, number, number];
  centroid: [number, number];
  rotation: number;
  edges: EdgeSignature;
  classification: PieceClassification;
  confidence: number;
  area: number;
}

export interface PieceDetail extends PieceMetadata {
  piece_image_base64: string | null;
}

export interface DebugResponse {
  segmentation_mask_base64: string | null;
  contours_overlay_base64: string | null;
  edges_overlay_base64: string | null;
  piece_count: number;
  processing_time_ms: number;
}

export interface AnalyzeResponse {
  status: "processing" | "completed";
  progress: number;
}
