import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import UploadDropzone from "../components/UploadDropzone";
import ActionButton from "../components/buttons/ActionButton";
import { useUploadImage } from "../hooks/useUploadImage";

export default function Home() {
  const navigate = useNavigate();
  const { uploading, error, upload } = useUploadImage();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  function handleFileSelected(file: File) {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  }

  async function handleAnalyze() {
    if (!selectedFile) return;
    const result = await upload(selectedFile);
    if (result) {
      navigate(`/analyzer/${result.puzzle_id}`);
    }
  }

  return (
    <Layout>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <h1 style={{ color: "#fff", marginBottom: 10 }}>Solve your puzzle, piece by piece</h1>
        <p style={{ color: "rgba(255,255,255,0.85)", fontSize: 16 }}>
          Upload a photo of your scattered jigsaw pieces. We will detect each one, tag its
          edges, and figure out which pieces make up the border.
        </p>
      </div>

      <div className="card" style={{ maxWidth: 640, margin: "0 auto" }}>
        {previewUrl ? (
          <div>
            <img
              src={previewUrl}
              alt="Selected puzzle photo preview"
              style={{
                width: "100%",
                maxHeight: 360,
                objectFit: "contain",
                borderRadius: 8,
                background: "var(--light-gray)",
                marginBottom: 16,
              }}
            />
            <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
              <ActionButton
                variant="secondary"
                disabled={uploading}
                onClick={() => {
                  setPreviewUrl(null);
                  setSelectedFile(null);
                }}
              >
                Choose a different photo
              </ActionButton>
              <ActionButton variant="primary" disabled={uploading} onClick={handleAnalyze}>
                {uploading ? "Uploading…" : "Detect pieces"}
              </ActionButton>
            </div>
          </div>
        ) : (
          <UploadDropzone onFileSelected={handleFileSelected} disabled={uploading} />
        )}

        {error && (
          <p style={{ color: "var(--error)", marginTop: 16, textAlign: "center" }}>{error}</p>
        )}
      </div>
    </Layout>
  );
}
