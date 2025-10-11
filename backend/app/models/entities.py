from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    original_language: Mapped[str] = mapped_column(String(32), default="fr")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scenes: Mapped[list["Scene"]] = relationship(
        back_populates="book", cascade="all, delete-orphan", order_by="Scene.index"
    )


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(256))
    summary: Mapped[str | None] = mapped_column(Text)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)

    book: Mapped[Book] = relationship(back_populates="scenes")
    sentences: Mapped[list["Sentence"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan", order_by="Sentence.index"
    )
    vocabulary: Mapped[list["Vocabulary"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan"
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan", order_by="Question.id"
    )


class Sentence(Base):
    __tablename__ = "sentences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"))
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)

    scene: Mapped[Scene] = relationship(back_populates="sentences")


class Vocabulary(Base):
    __tablename__ = "vocabulary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"))
    term: Mapped[str] = mapped_column(String(128), nullable=False)
    part_of_speech: Mapped[str | None] = mapped_column(String(64))
    definition: Mapped[str | None] = mapped_column(Text)
    example_sentence: Mapped[str | None] = mapped_column(Text)

    scene: Mapped[Scene] = relationship(back_populates="vocabulary")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"))
    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    scene: Mapped[Scene] = relationship(back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.id"
    )


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    question: Mapped[Question] = relationship(back_populates="options")
