import re


def clean_text(text):
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Normalize spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Preserve paragraph boundaries
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_sentences(text):
    """
    Split text into sentences while keeping
    punctuation attached to the sentence.
    """

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text.strip()
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def split_long_sentence(sentence, chunk_size):
    """
    Last-resort fallback for a sentence that
    is itself larger than chunk_size.
    """

    words = sentence.split()

    chunks = []
    current = ""

    for word in words:

        candidate = (
            f"{current} {word}"
            if current
            else word
        )

        if len(candidate) <= chunk_size:

            current = candidate

        else:

            if current:
                chunks.append(current)

            current = word

    if current:
        chunks.append(current)

    return chunks


def chunk_text(
    text,
    chunk_size=1200,
    overlap_sentences=1
):

    text = clean_text(text)

    if not text:
        return []


    # --------------------------------------------------
    # First preserve paragraphs
    # --------------------------------------------------

    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]


    # --------------------------------------------------
    # Convert paragraphs → sentences
    # --------------------------------------------------

    sentences = []

    for paragraph in paragraphs:

        paragraph_sentences = split_sentences(
            paragraph
        )

        sentences.extend(
            paragraph_sentences
        )


    # --------------------------------------------------
    # Build chunks from complete sentences
    # --------------------------------------------------

    chunks = []

    current = []
    current_length = 0


    for sentence in sentences:

        # Handle a sentence that is too large
        if len(sentence) > chunk_size:

            if current:

                chunks.append(
                    " ".join(current)
                )

                current = []
                current_length = 0


            long_chunks = split_long_sentence(
                sentence,
                chunk_size
            )

            chunks.extend(
                long_chunks
            )

            continue


        extra_length = (
            len(sentence)
            if not current
            else len(sentence) + 1
        )


        # Would this sentence exceed our target?
        if (
            current
            and current_length + extra_length > chunk_size
        ):

            chunks.append(
                " ".join(current)
            )


            # Keep a small amount of sentence-level
            # context instead of arbitrary characters.
            if overlap_sentences > 0:

                current = current[
                    -overlap_sentences:
                ]

                current_length = len(
                    " ".join(current)
                )

            else:

                current = []
                current_length = 0


        current.append(sentence)

        current_length = len(
            " ".join(current)
        )


    if current:

        chunks.append(
            " ".join(current)
        )


    return [
        chunk.strip()
        for chunk in chunks
        if chunk.strip()
    ]