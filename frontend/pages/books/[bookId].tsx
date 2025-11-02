"use client";

import Link from "next/link";
import { useRouter } from "next/router";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";

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
  const [isReadingMode, setIsReadingMode] = useState(false);
  const [textScale, setTextScale] = useState(1);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [flashTarget, setFlashTarget] = useState<{ sentenceId: number; term: string } | null>(null);
  const sentenceRefs = useRef<Map<number, HTMLSpanElement>>(new Map());

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
    setFlashTarget(null);
    sentenceRefs.current.clear();
  }, [currentScene]);

  const selectedSentence: SentenceItem | null = useMemo(() => {
    if (!currentScene) return null;
    return currentScene.sentences.find((sentence) => sentence.id === selectedSentenceId) ?? null;
  }, [currentScene, selectedSentenceId]);

  const questions: Question[] = currentScene?.questions ?? [];
  const vocabularyGroups = useMemo(() => {
    if (!currentScene) {
      return [] as Array<{ label: string; items: SceneItem["vocabulary"] }>;
    }
    const grouped = new Map<string, SceneItem["vocabulary"]>();
    for (const item of currentScene.vocabulary) {
      const label = (item.part_of_speech || "Other").trim() || "Other";
      if (!grouped.has(label)) {
        grouped.set(label, []);
      }
      grouped.get(label)?.push(item);
    }
    return Array.from(grouped.entries()).map(([label, items]) => ({ label, items }));
  }, [currentScene]);

  const handleQuestionOptionClick = (questionId: number, optionId: number, isCorrect: boolean) => {
    setSelectedOptions((prev) => ({ ...prev, [questionId]: optionId }));
    setQuestionResults((prev) => ({ ...prev, [questionId]: isCorrect }));
  };

  const goToPrevious = useCallback(() => {
    setSceneIndex((prev) => Math.max(prev - 1, 0));
  }, []);

  const goToNext = useCallback(() => {
    if (!book) return;
    setSceneIndex((prev) => Math.min(prev + 1, book.scenes.length - 1));
  }, [book]);

  useEffect(() => {
    setIsTransitioning(true);
    const timeout = window.setTimeout(() => setIsTransitioning(false), 200);
    return () => window.clearTimeout(timeout);
  }, [sceneIndex]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goToPrevious();
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        goToNext();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [goToNext, goToPrevious]);

  const totalScenes = book?.scenes.length ?? 0;
  const progressRatio = totalScenes > 1 ? (sceneIndex + 1) / totalScenes : 1;

  const decreaseTextScale = () => setTextScale((value) => Math.max(0.85, Number((value - 0.05).toFixed(2))));
  const increaseTextScale = () => setTextScale((value) => Math.min(1.3, Number((value + 0.05).toFixed(2))));

  const handleVocabularyClick = (term: string) => {
    if (!currentScene) {
      return;
    }
    const normalized = term.trim().toLowerCase();
    const target = currentScene.sentences.find((sentence) =>
      sentence.original_text.toLowerCase().includes(normalized),
    );
    if (!target) {
      return;
    }
    setSelectedSentenceId(target.id);
    setFlashTarget({ sentenceId: target.id, term: term.trim() });
    const element = sentenceRefs.current.get(target.id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  useEffect(() => {
    if (!flashTarget) {
      return;
    }
    const timer = window.setTimeout(() => {
      setFlashTarget((prev) => (prev && prev.sentenceId === flashTarget.sentenceId ? null : prev));
    }, 1600);
    return () => window.clearTimeout(timer);
  }, [flashTarget]);

  return (
    <section>
      <Link href="/library" className="button secondary" style={{ marginBottom: "1.5rem" }}>
        ← Back to Library
      </Link>
      <div className="viewer-controls">
        <button
          type="button"
          className={`button secondary toggle${isReadingMode ? " active" : ""}`}
          onClick={() => setIsReadingMode((prev) => !prev)}
        >
          {isReadingMode ? "Exit Reading Mode" : "Reading Mode"}
        </button>
        <div className="text-size-controls">
          <span className="muted">Text size</span>
          <div className="text-size-buttons">
            <button type="button" className="button secondary" onClick={decreaseTextScale}>
              A-
            </button>
            <button type="button" className="button secondary" onClick={increaseTextScale}>
              A+
            </button>
          </div>
        </div>
      </div>
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
        <>
          <div className={`viewer-layout${isReadingMode ? " reading-mode" : ""}`}>
            <div
              className={`scene-main${isTransitioning ? " scene-transition" : ""}`}
              style={{ "--text-scale": `${textScale}` } as CSSProperties}
            >
            <header className="scene-header">
              <h1 className="scene-title">{currentScene.title || `Scene ${currentScene.index}`}</h1>
              <p className="muted">
                Scene {currentScene.index} of {book.scenes.length}
              </p>
            </header>
            {!isReadingMode && (
              <div className="scene-navigation top">
                <button
                  className="nav-button"
                  onClick={goToPrevious}
                  disabled={sceneIndex === 0}
                  aria-label="Previous scene"
                >
                  ←
                </button>
                <button
                  className="nav-button"
                  onClick={goToNext}
                  disabled={sceneIndex >= book.scenes.length - 1}
                  aria-label="Next scene"
                >
                  →
                </button>
              </div>
            )}
            {!isReadingMode && currentScene.summary && <p className="muted scene-summary">{currentScene.summary}</p>}
            <div className="scene-body">
              {currentScene.sentences.map((sentence) => (
                <span
                  key={sentence.id}
                  role="button"
                  tabIndex={0}
                  className={`sentence${sentence.id === selectedSentenceId ? " active" : ""}${
                    flashTarget && flashTarget.sentenceId === sentence.id ? " flash" : ""
                  }`}
                  onClick={() =>
                    setSelectedSentenceId((prev) => (prev === sentence.id ? null : sentence.id))
                  }
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedSentenceId((prev) => (prev === sentence.id ? null : sentence.id));
                    }
                  }}
                  aria-pressed={sentence.id === selectedSentenceId}
                  ref={(element) => {
                    if (!element) {
                      sentenceRefs.current.delete(sentence.id);
                    } else {
                      sentenceRefs.current.set(sentence.id, element);
                    }
                  }}
                >
                  {sentence.original_text}
                </span>
              ))}
            </div>
            {isReadingMode && (
              <div className="scene-navigation bottom">
                <button
                  className="nav-button"
                  onClick={goToPrevious}
                  disabled={sceneIndex === 0}
                  aria-label="Previous scene"
                >
                  ←
                </button>
                <button
                  className="nav-button"
                  onClick={goToNext}
                  disabled={sceneIndex >= book.scenes.length - 1}
                  aria-label="Next scene"
                >
                  →
                </button>
              </div>
            )}
          </div>
          {!isReadingMode && (
            <aside className="scene-side">
              <div className="scene-bubble scene-translation">
                <h3>Sentence Translation</h3>
                {selectedSentence ? (
                  <p className="translation">{selectedSentence.translated_text}</p>
                ) : (
                  <p className="muted">Select a sentence to reveal its English translation.</p>
                )}
              </div>
              <div className="scene-bubble scene-vocab">
                <h3>Vocabulary Highlights</h3>
                {currentScene.vocabulary.length === 0 ? (
                  <p className="muted">No key vocabulary captured in this scene.</p>
                ) : (
                  <div className="vocab-groups">
                    {vocabularyGroups.map(({ label, items }) => (
                      <div key={label} className="vocab-group">
                        <h4 className="vocab-group-title">{label}</h4>
                        <ul className="vocab-list">
                          {items.map((item) => (
                            <li key={item.id}>
                              <button
                                type="button"
                                className="vocab-term-button"
                                onClick={() => handleVocabularyClick(item.term)}
                              >
                                <span className="vocab-term">{item.term}</span>
                                {item.definition && <span className="vocab-definition">{item.definition}</span>}
                              </button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </aside>
          )}
        </div>
        {!isReadingMode && questions.length > 0 && (
          <section className="questions-section scene-bubble">
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
                      Ce n&apos;est pas exact. La bonne réponse :{" "}
                      {question.options.find((option) => option.is_correct)?.text}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          </section>
        )}
          <div className="scene-progress">
            <span className="muted">
              Scene {sceneIndex + 1} of {totalScenes}
            </span>
            <div className="scene-progress-bar" aria-hidden>
              <div className="scene-progress-fill" style={{ width: `${Math.max(5, Math.round(progressRatio * 100))}%` }} />
            </div>
          </div>
        </>
      )}
    </section>
  );
};

export default BookViewerPage;
