from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm_service import process_text_and_cite

app = FastAPI(title="Sourcery API")

# Allow requests from Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CitationRequest(BaseModel):
    text: str
    model: str = "qwen3.5:9b"
    strictness: int = 2

class CitationResponse(BaseModel):
    annotated_text: str
    bibtex: str

@app.post("/cite", response_model=CitationResponse)
async def generate_citations(req: CitationRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
        
    try:
        result = process_text_and_cite(req.text, req.model, req.strictness)
        return CitationResponse(
            annotated_text=result["annotated_text"],
            bibtex=result["bibtex"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
