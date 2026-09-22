import axios from "axios";
import type {
  AnalyzeResponse,
  DebugResponse,
  PieceDetail,
  PieceMetadata,
  PuzzleSummary,
  UploadResponse,
} from "../types/puzzle";

// Vite's dev server and the production Docker image both proxy /api to the
// FastAPI backend (see vite.config.ts and the Dockerfile), so a relative
// base URL works in both environments without an env var to manage.
const api = axios.create({ baseURL: "/api" });

export async function uploadPuzzle(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("image", file);
  const { data } = await api.post<UploadResponse>("/puzzle/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function analyzePuzzle(
  puzzleId: string,
  phases: number[] = [1, 2, 3, 4, 5, 6]
): Promise<AnalyzeResponse> {
  const { data } = await api.post<AnalyzeResponse>(`/puzzle/${puzzleId}/analyze`, { phases });
  return data;
}

export async function getPuzzle(puzzleId: string): Promise<PuzzleSummary> {
  const { data } = await api.get<PuzzleSummary>(`/puzzle/${puzzleId}`);
  return data;
}

export async function getPieces(puzzleId: string): Promise<PieceMetadata[]> {
  const { data } = await api.get<PieceMetadata[]>(`/puzzle/${puzzleId}/pieces`);
  return data;
}

export async function getPiece(puzzleId: string, pieceId: string): Promise<PieceDetail> {
  const { data } = await api.get<PieceDetail>(`/puzzle/${puzzleId}/pieces/${pieceId}`);
  return data;
}

export async function getDebug(puzzleId: string): Promise<DebugResponse> {
  const { data } = await api.get<DebugResponse>(`/puzzle/${puzzleId}/debug`);
  return data;
}

export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    return detail || err.message;
  }
  return err instanceof Error ? err.message : "Unknown error";
}
