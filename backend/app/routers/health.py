from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
def home():
    return {"message": "Nerva RAG API running"}
