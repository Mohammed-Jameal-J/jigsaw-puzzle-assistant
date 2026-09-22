import { ImagePlus } from "lucide-react";
import { useRef, useState, type DragEvent } from "react";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/jpg"];

interface UploadDropzoneProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export default function UploadDropzone({ onFileSelected, disabled }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  function validateAndEmit(file: File) {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setLocalError("Please upload a JPEG or PNG photo of your puzzle pieces.");
      return;
    }
    setLocalError(null);
    onFileSelected(file);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) validateAndEmit(file);
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-disabled={disabled}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        style={{
          border: `2px dashed ${isDragging ? "var(--secondary-blue)" : "var(--border-color)"}`,
          borderRadius: 12,
          padding: "56px 24px",
          textAlign: "center",
          cursor: disabled ? "not-allowed" : "pointer",
          background: isDragging ? "var(--light-gray)" : "var(--white)",
          transition: "all 0.15s ease",
          opacity: disabled ? 0.6 : 1,
        }}
      >
        <div style={{ marginBottom: 12, display: "flex", justifyContent: "center", color: "#6b7280" }} aria-hidden="true">
          <ImagePlus size={40} />
        </div>
        <p style={{ fontWeight: 600, fontSize: 16, marginBottom: 6 }}>
          Drop a photo of your puzzle pieces here
        </p>
        <p style={{ color: "#6b7280", fontSize: 14 }}>or click to browse, JPEG or PNG</p>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png"
          hidden
          disabled={disabled}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) validateAndEmit(file);
            e.target.value = "";
          }}
        />
      </div>
      {localError && (
        <p style={{ color: "var(--error)", marginTop: 10, fontSize: 14 }}>{localError}</p>
      )}
    </div>
  );
}
