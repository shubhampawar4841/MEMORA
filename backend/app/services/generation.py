from app.config import GROQ_MODEL_NAME
from app.llm import client


def _build_messages(query: str, context: str):
    prompt = f"""
You are Nerva, a document question-answering assistant.

Answer the user's question using ONLY the provided context.

If the answer is not present in the context, say:

"I don't have enough information in the provided documents."

Do not invent facts.

Context:
----------------
{context}
----------------

Question:
{query}

Answer:
"""

    return [
        {
            "role": "system",
            "content": (
                "Answer questions using only the supplied document context."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]


def generate_answer(query: str, context: str):
    response = client.chat.completions.create(
        model=GROQ_MODEL_NAME,
        messages=_build_messages(query, context),
        temperature=0.1,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


def stream_answer(query: str, context: str):
    stream = client.chat.completions.create(
        model=GROQ_MODEL_NAME,
        messages=_build_messages(query, context),
        temperature=0.1,
        max_tokens=500,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        token = getattr(delta, "content", None)
        if token:
            yield token
