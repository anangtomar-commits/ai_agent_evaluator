from fastapi import FastAPI

from api.routes import router

app = FastAPI(
    title="AI Agent Evaluator — Text Extraction",
    description="Extracts section-wise text from BRD documents (.pdf or .docx).",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
