import { useEffect, useRef, useState } from "react";
import { analyzePuzzle, apiErrorMessage, getPuzzle } from "../services/api";
import type { PuzzleSummary } from "../types/puzzle";

const POLL_INTERVAL_MS = 600;

export function usePuzzleAnalyzer(puzzleId: string | undefined) {
  const [summary, setSummary] = useState<PuzzleSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!puzzleId || started.current) return;
    started.current = true;

    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout>;

    async function run() {
      try {
        await analyzePuzzle(puzzleId!, [1, 2, 3, 4, 5, 6]); // full pipeline now implemented
        poll();
      } catch (err) {
        if (!cancelled) setError(apiErrorMessage(err));
      }
    }

    async function poll() {
      try {
        const s = await getPuzzle(puzzleId!);
        if (cancelled) return;
        setSummary(s);
        if (s.status === "processing" || s.status === "uploaded") {
          pollTimer = setTimeout(poll, POLL_INTERVAL_MS);
        } else if (s.status === "failed") {
          setError(s.error || "Detection failed.");
        }
      } catch (err) {
        if (!cancelled) setError(apiErrorMessage(err));
      }
    }

    run();
    return () => {
      cancelled = true;
      clearTimeout(pollTimer);
    };
  }, [puzzleId]);

  return { summary, error };
}
