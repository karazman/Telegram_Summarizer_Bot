"""BART-based message summarization logic."""

import logging
import re
import threading
from collections import Counter
from typing import List, Dict, Optional


class MessageSummarizer:
    """Handle message summarization using BART model."""

    TOPIC_STOP_WORDS = {
        "aber", "auch", "das", "dass", "der", "die", "ein", "eine",
        "einer", "für", "hat", "ich", "ist", "mit", "nicht", "oder",
        "sich", "sie", "sind", "und", "von", "war", "wie", "wir", "zu",
        "about", "and", "are", "for", "from", "have", "that", "the",
        "this", "was", "were", "will", "with", "you",
    }
    DATE_PATTERN = re.compile(
        r"\b(?:\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?|"
        r"morgen|übermorgen|tomorrow|"
        r"montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        re.IGNORECASE,
    )
    DEADLINE_CONTEXT_PATTERN = re.compile(
        r"\b(?:deadline|frist|termin|appointment|meeting|fällig|"
        r"spätestens|bis|am|um|by|until|due|on)\b",
        re.IGNORECASE,
    )
    ACTION_PATTERN = re.compile(
        r"\b(?:ich werde|ich kümmere mich|ich (?:schicke|sende|prüfe|kläre|"
        r"übernehme|erledige)|wir werden|wir müssen|übernehme ich|todo|"
        r"follow[- ]?up|i will|i'll|we need to)\b",
        re.IGNORECASE,
    )
    
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
        """Build a speaker-aware, topic-grouped transcript for BART."""
        records = self.prepare_message_records(messages)
        topic_groups = self.group_related_messages(records)
        transcript_lines = [
            f"Discussion involved {len({record['speaker'] for record in records})} "
            "distinct participants across the topics below."
        ]

        for index, group in enumerate(topic_groups, start=1):
            participant_count = len(group["speakers"])
            transcript_lines.append(
                f"Topic {index} was discussed by {participant_count} distinct "
                f"participant{'s' if participant_count != 1 else ''}:"
            )

            for record in group["messages"]:
                line = f"[{record['speaker']}]: {record['text']}"
                weight = (
                    self.priority_weight
                    if record["username"] == self.priority_username
                    else 1
                )
                transcript_lines.extend([line] * weight)

        return "\n".join(transcript_lines)

    def prepare_message_records(self, messages: List[Dict]) -> List[Dict]:
        """Normalize messages and assign stable pseudonyms to raw speakers."""
        speaker_labels = {}
        records = []

        for message in messages:
            text = message.get("message", "").strip()

            if not text or text.startswith("/"):
                continue

            speaker_key = str(
                message.get("user_id")
                or message.get("username")
                or "unknown"
            ).lower()
            speaker_labels.setdefault(
                speaker_key,
                f"participant_{len(speaker_labels) + 1}",
            )
            records.append({
                "speaker": speaker_labels[speaker_key],
                "username": str(message.get("username", "")).lower(),
                "text": text,
                "date": message.get("date", ""),
            })

        return records

    def discussion_statistics(self, messages: List[Dict]) -> Dict:
        """Calculate raw discussion statistics before priority weighting."""
        records = self.prepare_message_records(messages)
        groups = self.group_related_messages(records)
        return {
            "source_message_count": len(records),
            "distinct_participant_count": len({item["speaker"] for item in records}),
            "topic_participant_counts": [len(group["speakers"]) for group in groups],
        }

    def topic_terms(self, text: str) -> set[str]:
        """Return meaningful terms used for conservative topic grouping."""
        return {
            term
            for term in re.findall(r"[\wäöüß]{4,}", text.lower())
            if term not in self.TOPIC_STOP_WORDS
        }

    def group_related_messages(self, records: List[Dict]) -> List[Dict]:
        """Group messages only when they share a meaningful topic term."""
        groups = []

        for record in records:
            terms = self.topic_terms(record["text"])
            matching_group = next(
                (
                    group
                    for group in groups
                    if terms and terms.intersection(group["terms"])
                ),
                None,
            )

            if matching_group is None:
                groups.append({
                    "messages": [record],
                    "speakers": {record["speaker"]},
                    "terms": set(terms),
                })
            else:
                matching_group["messages"].append(record)
                matching_group["speakers"].add(record["speaker"])
                matching_group["terms"].update(terms)

        return groups

    def detect_optional_sections(self, records: List[Dict]) -> Dict[str, List[str]]:
        """Create English-only facts for source-backed optional sections."""
        sections = {
            "Upcoming deadlines": [],
            "Next steps": [],
            "Open questions": [],
        }

        for record in records:
            text = " ".join(record["text"].split())

            has_explicit_deadline = re.search(
                r"\b(?:deadline|frist|termin|appointment|fällig|due)\b",
                text,
                re.IGNORECASE,
            )
            has_contextual_date = (
                self.DATE_PATTERN.search(text)
                and self.DEADLINE_CONTEXT_PATTERN.search(text)
            )

            if has_explicit_deadline or has_contextual_date:
                date_match = self.DATE_PATTERN.search(text)
                if date_match:
                    deadline = f"A deadline or appointment was mentioned for {date_match.group(0)}."
                else:
                    deadline = "A deadline or appointment was mentioned."
                sections["Upcoming deadlines"].append(deadline)
            if self.ACTION_PATTERN.search(text):
                sections["Next steps"].append(
                    "A participant committed to a follow-up action."
                )
            if text.endswith("?"):
                sections["Open questions"].append(
                    "An open question remained unresolved."
                )

        return {
            title: list(dict.fromkeys(items))
            for title, items in sections.items()
            if items
        }

    def append_optional_sections(self, summary: str, sections: Dict[str, List[str]]) -> str:
        """Append non-empty, source-backed sections to the generated recap."""
        output = [summary]

        for title, items in sections.items():
            output.append(f"{title}:\n" + "\n".join(items))

        return "\n\n".join(output)

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
        """Summarize one BART-sized piece as an English moderator recap."""
        english_input = (
            "English moderator recap of the group discussion. "
            "Synthesize themes and avoid quoting individual messages.\n"
            f"{text}"
        )
        result = self.get_pipeline()(
            english_input,
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
        records = self.prepare_message_records(selected)
        participant_count = len({record["speaker"] for record in records})
        optional_sections = self.detect_optional_sections(records)
        logging.info(
            "Summarizing %s source messages from %s distinct participants.",
            len(records),
            participant_count,
        )
        logging.info(
            "Detected %s deadlines, %s action items, and %s open questions.",
            len(optional_sections.get("Upcoming deadlines", [])),
            len(optional_sections.get("Next steps", [])),
            len(optional_sections.get("Open questions", [])),
        )

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
        topic_counts = self.discussion_statistics(selected)["topic_participant_counts"]
        evidence = (
            "Write the final recap in English only. "
            f"Discussion evidence: {participant_count} distinct participants. "
            "Distinct participants per detected topic: "
            f"{', '.join(str(count) for count in topic_counts)}."
        )
        combined = f"{evidence} {combined}"
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

        summary = self.append_optional_sections(
            self.format_as_paragraphs(final_text),
            optional_sections,
        )
        logging.info("Summary finished.")
        return summary
