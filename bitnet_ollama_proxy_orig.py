from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os

app = FastAPI()

# BitNet backend address
BITNET_URL = os.getenv("BITNET_URL", "http://localhost:8001/v1/chat/completions")

@app.get("/api/tags")
async def list_models():
    """Ollama expects this to list available models."""
    return {"models": [{"name": "bitnet-b158-2b", "modified_at": "now"}]}

@app.post("/api/generate")
async def generate(request: Request):
    """Translate Ollama request schema -> BitNet chat format."""
    data = await request.json()
    prompt = data.get("prompt", "")
    model = data.get("model", "bitnet-b158-2b")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": data.get("max_tokens", 256),
        "temperature": data.get("temperature", 0.7)
    }

    try:
        r = requests.post(BITNET_URL, json=payload, timeout=600)
        r.raise_for_status()
        res = r.json()
        content = res["choices"][0]["message"]["content"]
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    # Ollama expects a streaming-like text block in one chunk
    return JSONResponse(content={
        "model": model,
        "created_at": "",
        "response": content,
        "done": True
    })

@app.get("/api/version")
async def version():
    return {"version": "bitnet-proxy-1.0"}
