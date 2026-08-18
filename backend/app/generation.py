import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError(
        "GROQ_API_KEY is missing. "
        "Create a .env file in the backend directory."
    )


client = Groq(
    api_key=api_key
)


MODEL_NAME = "openai/gpt-oss-20b"

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

        model=MODEL_NAME,

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