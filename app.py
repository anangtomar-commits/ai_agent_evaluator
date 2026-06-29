from fastapi import FastAPI

from api.routes import router as extraction_router
from api.routes_requirements import router as requirements_router

app = FastAPI(
    title="AI Agent Evaluator",
    description="Extracts text and structured requirements from BRD documents (.pdf or .docx).",
    version="0.2.0",
)

app.include_router(extraction_router)
app.include_router(requirements_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
