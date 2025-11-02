from __future__ import annotations

import json
import os
import logging
from typing import Any

import vertexai
from tenacity import Retrying, stop_after_attempt, wait_exponential
from vertexai.generative_models import GenerativeModel, GenerationConfig

from app.config import get_settings


class GeminiService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.google_project_id:
            raise RuntimeError("Google Cloud project id is not configured.")
        if settings.google_credentials_path:
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", settings.google_credentials_path)

        vertexai.init(project=settings.google_project_id, location=settings.vertex_location)
        self._model = GenerativeModel(settings.gemini_model)
        self._generation_config = GenerationConfig(response_mime_type="application/json")
        self._max_retry = max(1, settings.max_retry_attempts)

    def _generate_json(self, prompt: str) -> Any:
        logger = logging.getLogger(__name__)
        logger.info("Sending Gemini request with prompt length=%d", len(prompt))
        print(f"[Gemini Debug] sending prompt length={len(prompt)}", flush=True)
        retryer = Retrying(
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(self._max_retry),
            reraise=True,
        )

        for attempt in retryer:
            with attempt:
                print(f"[Gemini Debug] Starting Gemini Request", flush=True)
                response = self._model.generate_content(prompt, generation_config=self._generation_config)
                print(f"[Gemini Debug] Gemini Request Recieved", flush=True)

                text_content = getattr(response, "text", None)
                if not text_content:
                    raise ValueError("Vertex AI response did not contain text content.")
                try:
                    return json.loads(text_content)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Vertex AI response was not valid JSON. {text_content}") from exc

        raise RuntimeError("Vertex AI request failed after retries.")

    def segment_chunk(
        self,
        english_sentences: list[str],
        french_sentences: list[str],
        chunk_index: int,
        total_chunks: int,
        previous_scene_summary: str | None = None,
    ) -> list[dict[str, object]]:
        numbered_sentences = []
        for idx, (english, french) in enumerate(zip(english_sentences, french_sentences), start=1):
            english_text = (english or "").strip()
            fallback = (french or "").strip()
            if english_text:
                numbered_sentences.append(f"{idx}. {english_text}")
            elif fallback:
                numbered_sentences.append(f"{idx}. [French] {fallback}")
            else:
                numbered_sentences.append(f"{idx}.")
        sentences_block = "\n".join(numbered_sentences)
        summary_block = (
            f"Summary of the previous scene:\n{previous_scene_summary.strip()}\n\n"
            if previous_scene_summary and previous_scene_summary.strip()
            else ""
        )
        prompt = (
            "You are segmenting a French novel into concise scenes.\n"
            f"You are analysing chunk {chunk_index + 1} of {total_chunks}.\n"
            f"{summary_block}"
            "Use the numbered English sentences below to decide where scenes start and end.\n"
            "Create a new scene only when the narrative clearly shifts—such as a change in setting, time, perspective, or major story beat.\n"
            "Aim for scenes that cover no more than roughly two printed pages (about 750-1000 words or ~4000 characters).\n"
            "If the text keeps going beyond that length without a major shift, introduce a new scene and mark it as continuing.\n"
            "If the sentences continue the same moment, keep them together even if the scene is longer than usual; scene boundaries matter more than raw length.\n"
            "Return JSON with an array named 'scenes'. Each scene must have fields:\n"
            "- title: short descriptive title\n"
            "- summary: one or two sentences in English summarizing the scene\n"
            "- start_sentence_index: 1-based index of the first sentence in this chunk that belongs to the scene\n"
            "- end_sentence_index: 1-based index of the last sentence in this chunk that belongs to the scene\n"
            "  (both indices are inclusive and must satisfy 1 <= start_sentence_index <= end_sentence_index <= number of sentences listed)\n"
            "If a scene begins before this chunk, include only the portion present here and set 'continues_from_previous' to true.\n"
            "If a scene continues in the next chunk, set 'continues_to_next' to true.\n"
            "Do not invent text. Preserve sentence order. Ensure all sentences in this chunk are assigned to exactly one scene.\n"
            "Numbered English sentences:\n"
            f"{sentences_block}"
        )
        payload = self._generate_json(prompt)
        scenes = payload.get("scenes", [])
        if not isinstance(scenes, list):
            raise ValueError("Gemini segmentation response missing 'scenes' list.")
        return scenes

    def extract_vocabulary(self, scene_text: str, translated_sentences: list[str]) -> list[dict[str, str]]:
        prompt = (
            "You are building a vocabulary list for advanced French learners.\n"
            "Given the original French scene text and English translations, identify key vocabulary terms.\n"
            "Return JSON with an array named 'vocabulary'. Each item must have:\n"
            "- term: the French word or expression\n"
            "- part_of_speech: part of speech (e.g., 'noun', 'verb', 'adjective')\n"
            "- definition: short English definition\n"
            "- example_sentence: the French sentence using the term\n"
            "Focus on non-trivial, scene-specific vocabulary.\n"
            f"French scene:\n{scene_text}\n\n"
            f"English sentences:\n{' '.join(translated_sentences)}"
        )
        payload = self._generate_json(prompt)
        items = payload.get("vocabulary", [])
        if not isinstance(items, list):
            raise ValueError("Gemini vocabulary response missing 'vocabulary' list.")
        return items

    def generate_questions(self, scene_text: str) -> list[dict[str, object]]:
        prompt = (
            "You are a French language instructor creating reading comprehension questions.\n"
            "Given the French scene below, craft exactly four multiple choice questions in French that test understanding of the passage.\n"
            "Each question must have four answer options.\n"
            "Return JSON with an array named 'questions'. Each question must contain:\n"
            "- prompt: the question text in French\n"
            "- options: an array of four option objects. Each option must have:\n"
            "  - text: the answer choice in French\n"
            "  - is_correct: boolean flag indicating whether the option is correct\n"
            "Ensure exactly one option per question is marked true.\n"
            f"French scene:\n{scene_text}"
        )
        payload = self._generate_json(prompt)
        questions = payload.get("questions", [])
        if not isinstance(questions, list):
            raise ValueError("Gemini question response missing 'questions' list.")
        return questions
