import re


# ============================================================
# CONFIG
# ============================================================

MAX_CHUNK_CHARS = 1200
MIN_CHUNK_CHARS = 200
OVERLAP_CHARS = 150


# ============================================================
# HEADING DETECTION
# ============================================================

def looks_like_heading(text: str) -> bool:

    text = text.strip()

    if not text:
        return False

    # Too long to realistically be a heading
    if len(text) > 100:
        return False

    # Usually headings don't end with punctuation
    if text.endswith((".", ",", ";", ":")):
        return False

    words = text.split()

    # Very long sentences are not headings
    if len(words) > 12:
        return False

    # Common heading-like patterns
    if text.isupper():
        return True

    # Title Case
    if len(words) <= 8:
        title_words = sum(
            1
            for word in words
            if word and word[0].isupper()
        )

        if title_words / len(words) >= 0.6:
            return True

    return False


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text: str) -> str:

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# SPLIT LONG BLOCK
# ============================================================

def split_long_block(text: str):

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    chunks = []
    current = ""

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        if (
            len(current)
            + len(sentence)
            + 1
            <= MAX_CHUNK_CHARS
        ):

            current = (
                f"{current} {sentence}"
                if current
                else sentence
            )

        else:

            if current:
                chunks.append(
                    current.strip()
                )

            current = sentence

    if current:
        chunks.append(
            current.strip()
        )

    return chunks


# ============================================================
# STRUCTURE-AWARE CHUNKING
# ============================================================

def chunk_text(text: str):

    text = clean_text(text)

    # --------------------------------------------------------
    # Break document into paragraphs / blocks
    # --------------------------------------------------------

    blocks = [
        block.strip()
        for block in text.split("\n\n")
        if block.strip()
    ]

    chunks = []

    current_section = None
    current_chunk = ""

    for block in blocks:

        # ----------------------------------------------------
        # Detect heading
        # ----------------------------------------------------

        if looks_like_heading(block):

            # Flush previous chunk
            if current_chunk:

                chunks.append(
                    current_chunk.strip()
                )

                current_chunk = ""

            current_section = block

            # Don't immediately create a chunk
            # containing only the heading.
            continue

        # ----------------------------------------------------
        # Add section context
        # ----------------------------------------------------

        if current_section:

            if current_chunk:

                candidate = (
                    f"{current_chunk}\n{block}"
                )

            else:

                candidate = (
                    f"{current_section}\n{block}"
                )

        else:

            candidate = (
                f"{current_chunk}\n{block}"
                if current_chunk
                else block
            )

        # ----------------------------------------------------
        # Chunk size check
        # ----------------------------------------------------

        if len(candidate) <= MAX_CHUNK_CHARS:

            current_chunk = candidate

        else:

            # Save current chunk
            if current_chunk:

                chunks.append(
                    current_chunk.strip()
                )

            # Handle oversized block
            if len(block) > MAX_CHUNK_CHARS:

                split_chunks = split_long_block(
                    block
                )

                for split_chunk in split_chunks:

                    if current_section:

                        chunks.append(
                            f"{current_section}\n"
                            f"{split_chunk}"
                        )

                    else:

                        chunks.append(
                            split_chunk
                        )

                current_chunk = ""

            else:

                if current_section:

                    current_chunk = (
                        f"{current_section}\n"
                        f"{block}"
                    )

                else:

                    current_chunk = block

    # --------------------------------------------------------
    # Final chunk
    # --------------------------------------------------------

    if current_chunk:

        chunks.append(
            current_chunk.strip()
        )

    # --------------------------------------------------------
    # Remove tiny chunks
    # --------------------------------------------------------

    cleaned_chunks = []

    for chunk in chunks:

        chunk = chunk.strip()

        if len(chunk) >= MIN_CHUNK_CHARS:

            cleaned_chunks.append(chunk)

        elif cleaned_chunks:

            # Merge tiny trailing content
            merged = (
                cleaned_chunks[-1]
                + "\n"
                + chunk
            )

            if len(merged) <= MAX_CHUNK_CHARS:

                cleaned_chunks[-1] = merged

            else:

                cleaned_chunks.append(chunk)

        else:

            cleaned_chunks.append(chunk)

    return cleaned_chunks