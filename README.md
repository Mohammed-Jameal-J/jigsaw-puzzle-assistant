# Jigsaw Puzzle Assistant

A computer-vision MVP that takes a photo of scattered physical jigsaw pieces
and detects each piece, classifies its edges (tab/hole/flat), and works out
which pieces form the border. Monolithic app: one FastAPI backend serves
both the JSON API and the built React frontend on a single port.

## Status: Phases 1-6 complete + interactive canvas

| Phase | What | Status |
|---|---|---|
| 1 | Image upload | ✅ |
| 2 | Piece detection (OpenCV contours) | ✅ — 99.5-99.7% success rate, ~500-1250ms on a 4000x3000 photo (well under the 5s budget) |
| 3 | Piece ID assignment (P0001...) | ✅ |
| 4 | Border/corner classification | ✅ — exactly 4 corners, verified across 12+ independent test runs (different seeds/sizes) |
| 5 | Edge classification (tab/hole/flat) | ✅ — 96% accuracy on the synthetic test set (spec target: 80%) |
| 6 | Rotation detection | ✅ — with an inherent ambiguity, see below |
| Interactive canvas: drag/select | ✅ — native `<canvas>` rendering (not 1000 DOM nodes), click to inspect, drag to reposition, "Reset positions" |

## Quick start

### Docker (recommended)
```bash
docker-compose up --build
```
Open **http://localhost:8000**. If that port is taken, edit the `ports` line
in `docker-compose.yml` (e.g. `"8531:8000"`) — only the number before the
colon matters, the container always listens on 8000 internally.

### Local dev (without Docker)
```bash
# backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** (the Vite dev server proxies `/api` to
`:8000` — see `frontend/vite.config.ts`). For a production-style single-port
run, `npm run build` in `frontend/` first, then hit `:8000` directly —
`backend/main.py` serves `frontend/dist` once it exists.

### Get a test photo
There's no sample image bundled (keeps the repo small). Generate one:
```bash
python scripts/generate_synthetic_puzzle.py --out uploads/test.jpg
```
This renders a photo-realistic *scattered* puzzle (not assembled) with real
tab/hole/flat piece silhouettes on a table background, plus a
`test_ground_truth.json` alongside it with the true answer for every piece.
Upload `test.jpg` through the UI.

## Running the tests
```bash
cd backend
pip install -r requirements.txt   # includes pytest
python -m pytest tests/ -v
```
8 tests, all against a real generated puzzle (not mocks) — piece count,
timing, ID sequencing, bbox validity, edge classification accuracy, and
border/corner/rotation sanity checks.

```bash
# end-to-end pipeline check with pass/fail against the spec's hard requirements
python scripts/test_pipeline.py
```

## Project structure
```
backend/
  main.py                  FastAPI entrypoint; also serves the built frontend
  app/api/routes.py        All endpoints
  app/cv/                  OpenCV pipeline: preprocessing, segmentation,
                            feature extraction, rotation, edge analysis
  app/services/            Orchestration: image upload, piece detection
  app/database/storage.py  File-based JSON storage (no DB, per spec)
  tests/                   pytest suite, generates its own test fixtures
frontend/
  src/pages/                Home (upload) -> Analyzer (progress) -> Results
  src/components/           Upload dropzone, interactive canvas (drag/select),
                             piece thumbnail grid + inspector, debug panel
                             (mask/contours/edges overlays)
scripts/
  generate_synthetic_puzzle.py   Test data generator (see above)
  test_pipeline.py               CLI smoke test against ground truth
```

## API
| Endpoint | Purpose |
|---|---|
| `POST /api/puzzle/upload` | Upload a photo |
| `POST /api/puzzle/{id}/analyze` | Run detection (phases 1-6) |
| `GET /api/puzzle/{id}` | Status + counts |
| `GET /api/puzzle/{id}/pieces` | All piece metadata |
| `GET /api/puzzle/{id}/pieces/{piece_id}` | One piece, with its cropped image |
| `GET /api/puzzle/{id}/image` | The original uploaded photo (for client-side thumbnail cropping) |
| `GET /api/puzzle/{id}/debug` | Segmentation mask / contour overlay / edge-classification overlay, as images |

## Known limitations

**Border count is close but not exact.** Corner detection is now exact
(4/4, structurally guaranteed — see below), but border classification is
still plain per-edge thresholding with no equivalent structural constraint
to lean on, so it typically lands within ~5% of the true count rather than
matching it exactly.

**Rotation is only meaningful modulo 90°.** A solid-color square piece has
4-fold rotational symmetry and no printed image to break it, so "which side
is the true original top" isn't recoverable from a single piece in
isolation — only actually fitting pieces together (Phase 7+, out of scope)
would resolve that. `rotation` reports a consistent per-piece orientation
estimate, not a recovered "original" orientation.

**No real-photo testing.** Everything above is validated against the
synthetic generator, which is realistic (actual tab/hole geometry, table
background, varied colors/rotations) but still not a real photograph —
real lighting, shadows, and piece materials will likely need threshold
retuning in `app/cv/segmentation.py` and `app/cv/preprocessing.py`. In
particular, `HOLE_DEPTH_CORRECTION` in `app/cv/edge_analysis.py` (see next
section) is calibrated against this specific generator/JPEG-quality
setting and may need re-measuring against a different image source.

## Design notes worth knowing about

- **Core-shape extraction (Phase 6) uses contour simplification, not
  morphology.** An earlier attempt used morphological open/close to strip
  tabs/holes off a piece's silhouette; this turned out to not fully work at
  the pixel scale a single piece occupies, even with generously oversized
  kernels — verified with isolated test cases, not just insufficient
  tuning. Switched to `cv2.approxPolyDP` with an epsilon tuned to collapse
  bump curves while preserving the piece's genuinely sharp corners; more
  robust and much simpler. See `app/cv/rotation.py`'s module docstring.

- **Holes measure shallower than tabs, systematically.** Measured against
  ground truth, a true hole's indentation reads at ~68% of a true tab's
  protrusion for the same generated bump depth — almost certainly
  JPEG/anti-aliasing softening concave regions more than convex ones at
  this pixel scale. `HOLE_DEPTH_CORRECTION` in `app/cv/edge_analysis.py`
  compensates for this measured, reproducible bias (not just per-image
  noise — confirmed via a full confusion-matrix analysis, not a single
  before/after comparison).

- **Corner detection uses a global structural constraint, not a per-piece
  threshold.** A rectangular assembled puzzle always has exactly 4
  corners — a known fact the pipeline wasn't using anywhere at first, even
  though per-piece edge classification alone (96% accurate per edge) still
  produces enough outliers across ~4000 edges to overshoot the corner count
  2-3x if each piece is judged independently. Ranking every piece by "how
  flat do its best 2 edges look" and taking the global top 4
  (`_apply_global_corner_selection` in `app/services/piece_detector.py`)
  turns that same noisy per-edge signal into a comparison, which only needs
  the noise to be smaller than the corner/non-corner gap on average, not
  small in absolute terms. Verified exact (4/4) across 12+ independent
  synthetic puzzles at multiple sizes before trusting it.

- **The backend serves the built frontend itself** (`main.py`) rather than
  running two processes in one container — simpler and more reliable than
  the two-process-in-one-container approach, with a proper SPA fallback so
  routes like `/results/{id}` work on a hard refresh, not just client-side
  navigation.

- **The interactive canvas renders to a native `<canvas>`, not one DOM
  node per piece.** At up to hundreds of pieces, hit-testing and redrawing
  a canvas element stays smooth; a real DOM element per draggable piece
  would not. Capped at 300 pieces on-canvas for a 1000-piece puzzle to keep
  drag interaction responsive — the Grid view (thumbnail grid, same
  click-to-inspect) covers browsing the rest.
