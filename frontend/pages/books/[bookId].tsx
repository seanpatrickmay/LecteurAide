import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";

import { Book, Question, SceneItem, SentenceItem, fetchBook } from "../../lib/api";

const BookViewerPage = () => {
  const router = useRouter();
  const { bookId } = router.query;

  const [book, setBook] = useState<Book | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sceneIndex, setSceneIndex] = useState(0);
  const [selectedSentenceId, setSelectedSentenceId] = useState<number | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<Record<number, number | null>>({});
  const [questionResults, setQuestionResults] = useState<Record<number, boolean | null>>({});

  useEffect(() => {
    const id = Array.isArray(bookId) ? bookId[0] : bookId;
    if (!id) return;
    const load = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await fetchBook(id);
        setBook(data);
        setSceneIndex(0);
        setSelectedSentenceId(null);
        setSelectedOptions({});
        setQuestionResults({});
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load the book.");
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [bookId]);

  const currentScene: SceneItem | null = useMemo(() => {
    if (!book) return null;
    return book.scenes[sceneIndex] ?? null;
  }, [book, sceneIndex]);

  useEffect(() => {
    setSelectedSentenceId(null);
    setSelectedOptions({});
    setQuestionResults({});
  }, [currentScene]);

  const selectedSentence: SentenceItem | null = useMemo(() => {
    if (!currentScene) return null;
    return currentScene.sentences.find((sentence) => sentence.id === selectedSentenceId) ?? null;
  }, [currentScene, selectedSentenceId]);

  const questions: Question[] = currentScene?.questions ?? [];

  const handleQuestionOptionClick = (questionId: number, optionId: number, isCorrect: boolean) => {
    setSelectedOptions((prev) => ({ ...prev, [questionId]: optionId }));
    setQuestionResults((prev) => ({ ...prev, [questionId]: isCorrect }));
  };

  const goToPrevious = () => {
    setSceneIndex((prev) => Math.max(prev - 1, 0));
  };

  const goToNext = () => {
    if (!book) return;
    setSceneIndex((prev) => Math.min(prev + 1, book.scenes.length - 1));
  };

  return (
    <section>
      <Link href="/library" className="button secondary" style={{ marginBottom: "1.5rem" }}>
        ← Back to Library
      </Link>
      {isLoading && <div className="card">Preparing your book…</div>}
      {error && (
        <div className="card" role="alert">
          {error}
        </div>
      )}
      {!isLoading && !error && book && !currentScene && (
        <div className="card" role="status">
          This book has not produced any scenes yet.
        </div>
      )}
      {!isLoading && !error && book && currentScene && (
        <div className="viewer-layout">
          <article className="scene-container">
            <header className="scene-header">
              <div>
                <h1 className="scene-title">{currentScene.title || `Scene ${currentScene.index}`}</h1>
                <p className="muted">
                  Scene {currentScene.index} of {book.scenes.length}
                </p>
              </div>
              <div className="scene-pagination">
                <button
                  className="button secondary"
                  onClick={goToPrevious}
                  disabled={sceneIndex === 0}
                  aria-label="Previous scene"
                >
                  ← Previous
                </button>
                <button
                  className="button"
                  onClick={goToNext}
                  disabled={sceneIndex >= book.scenes.length - 1}
                  aria-label="Next scene"
                >
                  Next →
                </button>
              </div>
            </header>
            {currentScene.summary && <p className="muted">{currentScene.summary}</p>}
            <div className="scene-body">
              {currentScene.sentences.map((sentence) => (
                <button
                  key={sentence.id}
                  type="button"
                  className={`sentence${sentence.id === selectedSentenceId ? " active" : ""}`}
                  onClick={() => setSelectedSentenceId(sentence.id)}
                  aria-pressed={sentence.id === selectedSentenceId}
                >
                  {sentence.original_text}
                  {" "}
                </button>
              ))}
            </div>
            {questions.length > 0 && (
              <section className="questions-section">
                <h2>Questions de compréhension</h2>
                <ol className="questions-list">
                  {questions.map((question) => (
                    <li key={question.id} className="question-card">
                      <p className="question-prompt">{question.prompt}</p>
                      <ul className="question-options">
                        {question.options.map((option) => (
                          <li key={option.id} className="question-option">
                            <button
                              type="button"
                              className={`question-option-button${
                                selectedOptions[question.id] === option.id ? ` selected` : ""
                              }${
                                selectedOptions[question.id] === option.id && questionResults[question.id] === true
                                  ? " correct"
                                  : ""
                              }${
                                selectedOptions[question.id] === option.id && questionResults[question.id] === false
                                  ? " incorrect"
                                  : ""
                              }${
                                selectedOptions[question.id] !== option.id && questionResults[question.id] === false && option.is_correct
                                  ? " reveal"
                                  : ""
                              }`}
                              onClick={() => handleQuestionOptionClick(question.id, option.id, option.is_correct)}
                              aria-pressed={selectedOptions[question.id] === option.id}
                            >
                              {option.text}
                            </button>
                          </li>
                        ))}
                      </ul>
                      {questionResults[question.id] === true && (
                        <p className="question-feedback success">Bonne réponse !</p>
                      )}
                      {questionResults[question.id] === false && (
                        <p className="question-feedback error">
                          Ce n'est pas exact. La bonne réponse : {" "}
                          {question.options.find((option) => option.is_correct)?.text}
                        </p>
                      )}
                    </li>
                  ))}
                </ol>
              </section>
            )}
          </article>
          <aside className="sidebar">
            <div>
              <h3>Sentence Translation</h3>
              {selectedSentence ? (
                <p className="translation">{selectedSentence.translated_text}</p>
              ) : (
                <p className="muted">Select a sentence to reveal its English translation.</p>
              )}
            </div>
            <div>
              <h3>Vocabulary Highlights</h3>
              {currentScene.vocabulary.length === 0 ? (
                <p className="muted">No key vocabulary captured in this scene.</p>
              ) : (
                <ul className="vocab-list">
                  {currentScene.vocabulary.map((item) => (
                    <li key={item.id}>
                      <div className="vocab-term">
                        {item.term}
                        {item.part_of_speech ? ` · ${item.part_of_speech}` : ""}
                      </div>
                      {item.definition && <div className="vocab-definition">{item.definition}</div>}
                      {item.example_sentence && <div className="vocab-definition">« {item.example_sentence} »</div>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        </div>
      )}
    </section>
  );
};

export default BookViewerPage;
