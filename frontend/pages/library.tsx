import Link from "next/link";
import { useEffect, useState } from "react";

import { BookSummary, deleteBook, fetchBooks } from "../lib/api";

const LibraryPage = () => {
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        const data = await fetchBooks();
        if (isMounted) {
          setBooks(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load your library.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    load();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleDelete = async (book: BookSummary) => {
    const confirmed = window.confirm(`Are you sure you want to delete "${book.title}"?`);
    if (!confirmed) {
      return;
    }
    setDeletingId(book.id);
    try {
      await deleteBook(book.id);
      setBooks((prev) => prev.filter((item) => item.id !== book.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete the book.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section>
      <h1>Your Library</h1>
      <p className="muted">Select a book to walk through its scenes and explore sentence translations.</p>
      {isLoading && <div className="card">Loading your books…</div>}
      {error && (
        <div className="card" role="alert">
          {error}
        </div>
      )}
      {!isLoading && !error && books.length === 0 && <div className="card">No books yet. Upload one to get started.</div>}
      <div className="library-grid">
        {books.map((book) => {
          const createdDate = new Date(book.created_at);
          const isDeleting = deletingId === book.id;
          return (
            <div key={book.id} className="card library-card">
              <Link href={`/books/${book.id}`} className="library-card-link">
                <h2>{book.title}</h2>
                <p className="muted">Added {createdDate.toLocaleString()}</p>
                <p>{book.scene_count} scenes processed</p>
              </Link>
              <div className="library-card-actions">
                <button
                  type="button"
                  className="button danger"
                  onClick={() => handleDelete(book)}
                  disabled={isDeleting}
                  aria-label={`Delete book ${book.title}`}
                >
                  {isDeleting ? "Deleting…" : "Delete book"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default LibraryPage;
