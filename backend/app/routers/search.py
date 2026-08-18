from fastapi import APIRouter

from app.schemas.search import SearchResponse
from app.services.retrieval import retrieve_for_search

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search_pdf(query: str, document_id: str | None = None):
    print("\n========== SEARCH ==========")
    print(f"Query: {query}")

    if document_id:
        print(f"Document ID: {document_id}")
    else:
        print("Searching across all documents.")

    results = retrieve_for_search(query, document_id)

    print(f"Final results: {len(results)}")
    print("========== SEARCH COMPLETE ==========\n")

    return {
        "query": query,
        "document_id": document_id,
        "results": results,
    }
