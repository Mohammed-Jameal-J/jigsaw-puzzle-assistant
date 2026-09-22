import type { DebugResponse } from "../types/puzzle";

export default function DebugPanel({ debug }: { debug: DebugResponse }) {
  const images: { label: string; src: string | null }[] = [
    { label: "Segmentation mask", src: debug.segmentation_mask_base64 },
    { label: "Detected contours", src: debug.contours_overlay_base64 },
    { label: "Edge classification", src: debug.edges_overlay_base64 },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
      {images.map(({ label, src }) => (
        <div key={label}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "#4b5563", marginBottom: 6 }}>{label}</p>
          {src ? (
            <img
              src={`data:image/png;base64,${src}`}
              alt={label}
              style={{ width: "100%", borderRadius: 8, border: "1px solid var(--border-color)" }}
            />
          ) : (
            <div
              style={{
                width: "100%",
                aspectRatio: "4/3",
                borderRadius: 8,
                border: "1px dashed var(--border-color)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#9ca3af",
                fontSize: 13,
              }}
            >
              Not available yet
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
