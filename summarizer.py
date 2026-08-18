"""
BART-based message summarization logic.
"""

from transformers import pipeline
from typing import List, Dict, Optional


class MessageSummarizer:
    """Handle message summarization using BART model."""
    
    def __init__(
        self,
        max_daily_messages: int = 500,
        priority_username: str = "michael_schredl",
        priority_weight: int = 2,
    ):
        """Initialize summarizer with BART model."""
        print("Loading BART summarization model...")
        self.summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn"
        )
        print("BART model loaded.")
        
        self.max_daily_messages = max_daily_messages
        self.priority_username = priority_username.lower()
        self.priority_weight = max(1, priority_weight)

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
        tokenizer = self.summarizer.tokenizer

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
        result = self.summarizer(
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

        if len(sentences) <= 2:
            return "\n\n".join(sentences)

        # Aim for roughly 3 short paragraphs.
        paragraph_count = min(3, len(sentences))
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

    def summarize_messages(self, messages: List[Dict]) -> Optional[str]:
        """Create a compact multi-paragraph daily summary."""
        selected = self.select_messages(messages)

        transcript = self.build_weighted_transcript(selected)

        if not transcript.strip():
            return None

        chunks = self.split_into_token_chunks(transcript)

        intermediate_summaries = []

        for index, chunk in enumerate(chunks, start=1):
            print(f"Summarizing chunk {index}/{len(chunks)}...")

            intermediate_summaries.append(
                self.summarize_chunk(
                    chunk,
                    max_length=130,
                    min_length=30,
                )
            )

        combined = " ".join(intermediate_summaries)

        # If intermediate result still too long, summarize again.
        final_chunks = self.split_into_token_chunks(
            combined,
            max_tokens=850
        )

        if len(final_chunks) == 1:
            final_text = self.summarize_chunk(
                final_chunks[0],
                max_length=220,
                min_length=80,
            )
        else:
            condensed = [
                self.summarize_chunk(
                    chunk,
                    max_length=110,
                    min_length=30,
                )
                for chunk in final_chunks
            ]

            combined_condensed = " ".join(condensed)

            final_chunk = self.split_into_token_chunks(
                combined_condensed,
                max_tokens=850
            )[0]

            final_text = self.summarize_chunk(
                final_chunk,
                max_length=220,
                min_length=80,
            )

        return self.format_as_paragraphs(final_text)
