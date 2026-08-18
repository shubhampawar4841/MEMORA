import re


def clean_text(text):
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces while preserving newlines
    text = re.sub(r"[ \t]+", " ", text)

    # Keep paragraph boundaries
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_recursive(
    text,
    chunk_size,
    overlap
):
    """
    Recursively split oversized text.

    Priority:
        paragraph
        ↓
        line
        ↓
        sentence
        ↓
        word
        ↓
        character
    """

    text = text.strip()

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]


    separators = [
        "\n\n",
        "\n",
        ". ",
        "? ",
        "! ",
        "; ",
        ", ",
        " ",
        ""
    ]


    # Find the best separator that actually
    # exists inside the text.
    separator = ""

    for candidate in separators:

        if candidate == "":
            separator = candidate
            break

        if candidate in text:

            separator = candidate
            break


    # --------------------------------------------------
    # Character fallback
    # --------------------------------------------------

    if separator == "":

        chunks = []

        start = 0

        while start < len(text):

            end = min(
                start + chunk_size,
                len(text)
            )

            chunk = text[
                start:end
            ].strip()

            if chunk:
                chunks.append(chunk)

            if end >= len(text):
                break

            start = max(
                0,
                end - overlap
            )

        return chunks


    # --------------------------------------------------
    # Split using selected separator
    # --------------------------------------------------

    pieces = text.split(separator)

    pieces = [
        piece.strip()
        for piece in pieces
        if piece.strip()
    ]


    if not pieces:
        return [text]


    chunks = []
    current = ""


    for piece in pieces:

        candidate = (
            f"{current}{separator}{piece}"
            if current
            else piece
        )


        if len(candidate) <= chunk_size:

            current = candidate

        else:

            if current:

                chunks.append(
                    current.strip()
                )


            # If this individual piece is
            # still too large, recursively
            # split it using a smaller separator.

            if len(piece) > chunk_size:

                smaller_chunks = split_recursive(
                    piece,
                    chunk_size,
                    overlap
                )

                chunks.extend(
                    smaller_chunks
                )

                current = ""

            else:

                current = piece


    if current:

        chunks.append(
            current.strip()
        )


    # --------------------------------------------------
    # Apply overlap between resulting chunks
    # --------------------------------------------------

    if overlap <= 0 or len(chunks) <= 1:
        return chunks


    overlapped = []

    for i, chunk in enumerate(chunks):

        if i == 0:

            overlapped.append(chunk)

            continue


        previous = chunks[i - 1]

        overlap_text = previous[
            -overlap:
        ]

        overlapped.append(
            f"{overlap_text} {chunk}"
        )


    return overlapped


def chunk_text(
    text,
    chunk_size=1200,
    overlap=150
):

    text = clean_text(text)

    if not text:
        return []


    return split_recursive(
        text,
        chunk_size,
        overlap
    )