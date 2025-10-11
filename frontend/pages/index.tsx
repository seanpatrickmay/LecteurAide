import { FormEvent, useRef, useState } from "react";

import { uploadBook } from "../lib/api";

const UploadPage = () => {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ processed: number; total: number } | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError("Please choose a PDF file.");
      return;
    }
    if (!title.trim()) {
      setError("Please provide a title for the book.");
      return;
    }
    setIsSubmitting(true);
    setIsProcessing(true);
    setError(null);
    setMessage(null);
    setProgress({ processed: 0, total: 0 });
    try {
      const response = await uploadBook(title.trim(), file, (processedChunks, totalChunks) => {
        setProgress({ processed: processedChunks, total: totalChunks });
      });
      setMessage(
        `Uploaded "${title.trim()}" (book #${response.book_id}) with ${response.scene_count} sections ready to review.`,
      );
      setTitle("");
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Please try again.");
    } finally {
      setIsSubmitting(false);
      setIsProcessing(false);
      setProgress(null);
    }
  };

  return (
    <section className="upload-page">
      <h1>Bring Your French Books to Life</h1>
      <p className="muted">
        Upload a French PDF, and we will segment it into rich scenes, translate each sentence, and surface vocabulary to
        help you explore it deeply.
      </p>
      <form className="card" onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="title">Book Title</label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Le Petit Prince"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="file">PDF File</label>
          <input
            id="file"
            type="file"
            ref={fileInputRef}
            accept="application/pdf"
            onChange={(event) => {
              const [selected] = event.target.files ?? [];
              setFile(selected ?? null);
            }}
            required
          />
        </div>
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Uploading…" : "Upload Book"}
        </button>
      </form>
      {isProcessing && progress && (
        <div className="card progress-card">
          <div className="progress-label">
            {progress.total > 0
              ? `Processing chunks ${progress.processed}/${progress.total}`
              : "Preparing upload…"}
          </div>
          <div className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{
                width:
                  progress.total > 0
                    ? `${Math.min(100, Math.round((progress.processed / progress.total) * 100))}%`
                    : "10%",
              }}
            />
          </div>
        </div>
      )}
      {message && <div className="card">{message}</div>}
      {error && (
        <div className="card" role="alert">
          {error}
        </div>
      )}
    </section>
  );
};

export default UploadPage;
