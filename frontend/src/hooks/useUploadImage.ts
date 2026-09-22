import { useState } from "react";
import { apiErrorMessage, uploadPuzzle } from "../services/api";
import type { UploadResponse } from "../types/puzzle";

interface UploadState {
  uploading: boolean;
  error: string | null;
  result: UploadResponse | null;
}

export function useUploadImage() {
  const [state, setState] = useState<UploadState>({
    uploading: false,
    error: null,
    result: null,
  });

  async function upload(file: File): Promise<UploadResponse | null> {
    setState({ uploading: true, error: null, result: null });
    try {
      const result = await uploadPuzzle(file);
      setState({ uploading: false, error: null, result });
      return result;
    } catch (err) {
      setState({ uploading: false, error: apiErrorMessage(err), result: null });
      return null;
    }
  }

  return { ...state, upload };
}
