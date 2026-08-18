from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL_NAME


if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing. "
        "Create a .env file in the backend directory."
    )


client = Groq(
    api_key=GROQ_API_KEY
)


def generate_answer(
    query: str,
    context: str
):

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


    response = client.chat.completions.create(

        model=GROQ_MODEL_NAME,

        messages=[

            {
                "role": "system",
                "content":
                    "Answer questions using only the supplied document context."
            },

            {
                "role": "user",
                "content": prompt
            }

        ],

        temperature=0.1,

        max_tokens=500

    )


    return response.choices[0].message.content.strip()
