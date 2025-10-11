import Link from "next/link";
import { useEffect, useState } from "react";

import { BookSummary, fetchBooks } from "../lib/api";

const LibraryPage = () => {
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
          return (
            <Link key={book.id} href={`/books/${book.id}`} className="card library-card">
              <h2>{book.title}</h2>
              <p className="muted">Added {createdDate.toLocaleString()}</p>
              <p>{book.scene_count} scenes processed</p>
            </Link>
          );
        })}
      </div>
    </section>
  );
};

export default LibraryPage;
