"""BART-based message summarization logic."""

import logging
import threading
from typing import List, Dict, Optional


class MessageSummarizer:
    """Handle message summarization using BART model."""
    
    def __init__(
        self,
        max_daily_messages: int = 500,
        priority_username: str = "michael_schredl",
        priority_weight: int = 2,
    ):
        """Initialize summarizer configuration without loading the model."""
        self.max_daily_messages = max_daily_messages
        self.priority_username = priority_username.lower()
        self.priority_weight = max(1, priority_weight)
        self._pipeline = None
        self._pipeline_lock = threading.Lock()

    def get_pipeline(self):
        """Load the BART model lazily on the first summary request."""
        if self._pipeline is None:
            with self._pipeline_lock:
                if self._pipeline is None:
                    from transformers import pipeline

                    logging.info("Loading BART summarization model.")
                    self._pipeline = pipeline(
                        "summarization",
                        model="facebook/bart-large-cnn",
                    )
                    logging.info("BART model loaded.")

        return self._pipeline

    def select_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Keep all messages where possible.
        
        If too many messages, priority messages are retained preferentially.
        They are NOT labelled specially in the final text.
        """
        if len(messages) <= self.max_daily_messages:
            return messages

        priority = [
            msg for msg in messages
            if msg["username"] == self.priority_username
        ]

        others = [
            msg for msg in messages
            if msg["username"] != self.priority_username
        ]

        remaining_slots = max(
            0,
            self.max_daily_messages - len(priority)
        )

        # Prefer the most recent non-priority messages.
        selected = priority + others[-remaining_slots:]

        # Restore chronological order.
        selected.sort(key=lambda item: item["date"])

        return selected[-self.max_daily_messages:]

    def build_weighted_transcript(self, messages: List[Dict]) -> str:
        """Build model input with moderate emphasis on priority messages."""
        transcript_lines = []

        for message in messages:
            text = message["message"].strip()

            if not text or text.startswith("/"):
                continue

            weight = (
                self.priority_weight
                if message["username"] == self.priority_username
                else 1
            )
            transcript_lines.extend([text] * weight)

        return "\n".join(transcript_lines)

    def split_into_token_chunks(self, text: str, max_tokens: int = 850) -> List[str]:
        """Split text into chunks that BART can process safely."""
        tokenizer = self.get_pipeline().tokenizer

        token_ids = tokenizer.encode(
            text,
            add_special_tokens=False,
            truncation=False,
        )

        chunks = []

        for start in range(0, len(token_ids), max_tokens):
            chunk_ids = token_ids[start:start + max_tokens]

            chunk_text = tokenizer.decode(
                chunk_ids,
                skip_special_tokens=True,
            )

            if chunk_text.strip():
                chunks.append(chunk_text)

        return chunks

    def summarize_chunk(self, text: str, max_length: int = 130, min_length: int = 35) -> str:
        """Summarize one BART-sized piece of text."""
        result = self.get_pipeline()(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False,
            truncation=True,
        )

        return result[0]["summary_text"].strip()

    def format_as_paragraphs(self, text: str) -> str:
        """Format generated summary into short paragraphs."""
        text = " ".join(text.split())

        sentences = []
        current = ""

        for char in text:
            current += char

            if char in ".!?":
                sentence = current.strip()

                if sentence:
                    sentences.append(sentence)

                current = ""

        if current.strip():
            sentences.append(current.strip())

        if len(sentences) <= 3:
            return "\n\n".join(sentences)

        paragraph_count = min(6, max(4, (len(sentences) + 1) // 2))
        paragraphs = [[] for _ in range(paragraph_count)]

        for index, sentence in enumerate(sentences):
            target = min(
                index * paragraph_count // len(sentences),
                paragraph_count - 1,
            )

            paragraphs[target].append(sentence)

        return "\n\n".join(
            " ".join(paragraph)
            for paragraph in paragraphs
            if paragraph
        )

    def deduplicate_summaries(self, summaries: List[str]) -> str:
        """Merge intermediate summaries while removing repeated sentences."""
        seen = set()
        unique_sentences = []

        for summary in summaries:
            for sentence in summary.replace("\n", " ").split(". "):
                sentence = sentence.strip()
                normalized = " ".join(sentence.lower().split()).rstrip(".!?")

                if normalized and normalized not in seen:
                    seen.add(normalized)
                    unique_sentences.append(sentence.rstrip(".") + ".")

        return " ".join(unique_sentences)

    def summarize_messages(self, messages: List[Dict]) -> Optional[str]:
        """Create a detailed, coherent multi-paragraph daily summary."""
        selected = self.select_messages(messages)
        logging.info("Summarizing %s messages.", len(selected))

        transcript = self.build_weighted_transcript(selected)

        if not transcript.strip():
            return None

        chunks = self.split_into_token_chunks(transcript)
        logging.info("Created %s token chunks.", len(chunks))

        intermediate_summaries = []

        for index, chunk in enumerate(chunks, start=1):
            logging.info("Summarizing chunk %s/%s", index, len(chunks))

            intermediate_summaries.append(
                self.summarize_chunk(
                    chunk,
                    max_length=180,
                    min_length=50,
                )
            )

        logging.info("First summarization pass finished.")
        combined = self.deduplicate_summaries(intermediate_summaries)
        logging.info("Starting final synthesis.")

        # If intermediate result still too long, summarize again.
        final_chunks = self.split_into_token_chunks(
            combined,
            max_tokens=850
        )

        if len(final_chunks) == 1:
            final_text = self.summarize_chunk(
                final_chunks[0],
                max_length=360,
                min_length=140,
            )
        else:
            condensed = [
                self.summarize_chunk(
                    chunk,
                    max_length=180,
                    min_length=50,
                )
                for chunk in final_chunks
            ]

            combined_condensed = self.deduplicate_summaries(condensed)

            final_chunk = self.split_into_token_chunks(
                combined_condensed,
                max_tokens=850
            )[0]

            final_text = self.summarize_chunk(
                final_chunk,
                max_length=360,
                min_length=140,
            )

        summary = self.format_as_paragraphs(final_text)
        logging.info("Summary finished.")
        return summary
