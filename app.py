from fastapi import FastAPI

from api.routes import router as extraction_router
from api.routes_requirements import router as requirements_router
from api.routes_classifier import router as classifier_router
from api.routes_scenarios import router as scenarios_router

app = FastAPI(
    title="AI Agent Evaluator",
    description="Extracts text, requirements, test strategies, and test scenarios from BRD documents (.pdf or .docx).",
    version="0.4.0",
)

app.include_router(extraction_router)
app.include_router(requirements_router)
app.include_router(classifier_router)
app.include_router(scenarios_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
