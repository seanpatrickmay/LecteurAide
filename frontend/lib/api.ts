export type VocabularyItem = {
  id: number;
  term: string;
  part_of_speech?: string | null;
  definition?: string | null;
  example_sentence?: string | null;
};

export type SentenceItem = {
  id: number;
  index: number;
  original_text: string;
  translated_text: string;
};

export type QuestionOption = {
  id: number;
  text: string;
  is_correct: boolean;
};

export type Question = {
  id: number;
  prompt: string;
  options: QuestionOption[];
};

export type SceneItem = {
  id: number;
  index: number;
  title?: string | null;
  summary?: string | null;
  original_text: string;
  sentences: SentenceItem[];
  vocabulary: VocabularyItem[];
  questions: Question[];
};

export type Book = {
  id: number;
  title: string;
  original_language: string;
  created_at: string;
  scenes: SceneItem[];
};

export type BookSummary = {
  id: number;
  title: string;
  created_at: string;
  scene_count: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || `Request failed with ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function fetchBooks(): Promise<BookSummary[]> {
  const res = await fetch(`${API_BASE_URL}/books`);
  return handleResponse<BookSummary[]>(res);
}

export async function fetchBook(bookId: number | string): Promise<Book> {
  const res = await fetch(`${API_BASE_URL}/books/${bookId}`);
  return handleResponse<Book>(res);
}

export async function deleteBook(bookId: number | string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/books/${bookId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || `Delete failed with ${res.status}`);
  }
}

export type UploadProgressHandler = (processedChunks: number, totalChunks: number) => void;

export async function uploadBook(
  title: string,
  file: File,
  onProgress?: UploadProgressHandler,
): Promise<{ book_id: number; scene_count: number }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", title);

  const res = await fetch(`${API_BASE_URL}/books/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok && res.status !== 202) {
    const message = await res.text();
    throw new Error(message || `Upload failed with ${res.status}`);
  }
  if (!res.body) {
    throw new Error("Upload response did not include a body.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: { book_id: number; scene_count: number } | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (value) {
      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r/g, "");
      let separatorIndex: number;
      while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, separatorIndex).trim();
        buffer = buffer.slice(separatorIndex + 2);
        if (!rawEvent.startsWith("data:")) {
          continue;
        }
        const payloadRaw = rawEvent.slice(5).trim();
        if (!payloadRaw) {
          continue;
        }
        const payload = JSON.parse(payloadRaw);
        if (payload.type === "progress" && onProgress) {
          onProgress(payload.processed_chunks ?? 0, payload.total_chunks ?? 0);
        } else if (payload.type === "completed") {
          finalResult = {
            book_id: payload.book_id,
            scene_count: payload.scene_count,
          };
        } else if (payload.type === "error") {
          try {
            await reader.cancel();
          } catch (err) {
            console.warn("Failed to cancel reader after error", err);
          }
          throw new Error(payload.message ?? "An error occurred while processing the book.");
        }
      }
    }
    if (done) {
      buffer += decoder.decode();
      buffer = buffer.replace(/\r/g, "");
      let separatorIndex: number;
      while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, separatorIndex).trim();
        buffer = buffer.slice(separatorIndex + 2);
        if (!rawEvent.startsWith("data:")) {
          continue;
        }
        const payloadRaw = rawEvent.slice(5).trim();
        if (!payloadRaw) {
          continue;
        }
        const payload = JSON.parse(payloadRaw);
        if (payload.type === "progress" && onProgress) {
          onProgress(payload.processed_chunks ?? 0, payload.total_chunks ?? 0);
        } else if (payload.type === "completed") {
          finalResult = {
            book_id: payload.book_id,
            scene_count: payload.scene_count,
          };
        } else if (payload.type === "error") {
          throw new Error(payload.message ?? "An error occurred while processing the book.");
        }
      }
      break;
    }
  }

  if (!finalResult) {
    throw new Error("Upload did not complete successfully.");
  }

  return finalResult;
}
