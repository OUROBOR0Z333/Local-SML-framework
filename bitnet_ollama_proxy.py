from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json, time, httpx
from langfuse import Langfuse
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LangFuse client
try:
    langfuse = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
        host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        debug=False  # Set to True for debugging, False for production
    )
    LANGFUSE_AVAILABLE = True
    # Verify the Langfuse client has the methods we need
    if not (hasattr(langfuse, 'start_span') and hasattr(langfuse, 'start_observation')):
        print("Langfuse client does not have required methods (start_span, start_observation) - incompatible version or API")
        LANGFUSE_AVAILABLE = False
except Exception as e:
    print(f"Langfuse initialization error: {e}")
    LANGFUSE_AVAILABLE = False
    langfuse = None

# BitNet backend address
BITNET_URL = os.getenv("BITNET_URL", "http://localhost:8000/v1/chat/completions")
BITNET_BASE_URL = os.getenv("BITNET_BASE_URL", "http://localhost:8000")

import random

# Define sampling rate for high-frequency endpoints (20% to reduce costs)
HIGH_FREQ_SAMPLING_RATE = 0.2  # 20% sampling

def should_sample_endpoint() -> bool:
    """Determine if we should create a trace for this request based on sampling rate."""
    return random.random() < HIGH_FREQ_SAMPLING_RATE

@app.get("/api/tags")
async def list_models():
    """Ollama expects this to list available models."""
    response_content = {"models": [{"model": "bitnet-b158-2b", "name": "bitnet-b158-2b", "modified_at": "now", "size": 1187801280, "digest": "sha256:dummy"}]}

    # Add LangFuse trace if available and should sample (for high-frequency endpoints)
    if LANGFUSE_AVAILABLE and langfuse and should_sample_endpoint():
        try:
            trace = langfuse.start_span(
                name="api-tags",
                input={"endpoint": "/api/tags"},
                metadata={"endpoint": "/api/tags", "service": "bitnet-proxy"}
            )
            trace.update(output=response_content)
        except Exception as e:
            print(f"Langfuse error in /api/tags: {e}")

    return response_content

@app.post("/api/generate")
async def generate(request: Request):
    """Translate Ollama request schema -> BitNet chat format."""
    trace = None
    generation = None

    try:
        data = await request.json()
        prompt = data.get("prompt", "")
        model = data.get("model", "bitnet-b158-2b")

        # Handle model names with tags (like "model:latest") by extracting just the base name
        base_model = model.split(':')[0] if ':' in model else model

        payload = {
            "model": base_model,  # Use the base model name without tag for BitNet
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": data.get("max_tokens", 256),
            "temperature": data.get("temperature", 0.7),
        }

        # Add LangFuse trace if available
        if LANGFUSE_AVAILABLE and langfuse:
            try:
                trace = langfuse.start_span(
                    name="api-generate",
                    input=data,
                    metadata={"endpoint": "/api/generate", "service": "bitnet-proxy"}
                )

                # Create a generation trace for the actual model call (using start_observation)
                try:
                    generation = langfuse.start_observation(
                        trace_context={"trace_id": trace.trace_id},  # Link to the parent span's trace
                        name="bitnet-generation",
                        as_type="generation",
                        input=payload,
                        model=base_model,
                    )
                except Exception as gen_error:
                    print(f"Langfuse generation linking error: {gen_error}. Creating unlinked generation.")
                    # If trace_id approach fails, create generation without linking to trace
                    generation = langfuse.start_observation(
                        name="bitnet-generation",
                        as_type="generation",
                        input=payload,
                        model=base_model,
                    )
            except Exception as e:
                print(f"Langfuse error in /api/generate trace setup: {e}")

        try:
            async with httpx.AsyncClient(timeout=600) as client:
                r = await client.post(BITNET_URL, json=payload)
                r.raise_for_status()
                res = r.json()
                content = res["choices"][0]["message"]["content"]

                # Update the generation with output if tracing is active
                if generation:
                    try:
                        generation.update(output={"content": content})
                        generation.end()
                    except Exception as e:
                        # If update and end fail, just try to end the generation
                        try:
                            generation.end()
                        except Exception as e2:
                            print(f"Langfuse generation end error: {e}, fallback error: {e2}")
        except httpx.HTTPStatusError as e:
            # Log the error to LangFuse if available
            if trace:
                try:
                    trace.score(
                        name="error",
                        value=0,
                        comment=f"HTTP error: {e.response.status_code}"
                    )
                except Exception as score_error:
                    print(f"Langfuse score error: {score_error}")

            return JSONResponse(status_code=e.response.status_code, content=e.response.json())
        except Exception as e:
            # Log the error to LangFuse if available
            if trace:
                try:
                    trace.score(
                        name="error",
                        value=0,
                        comment=f"Exception: {str(e)}"
                    )
                except Exception as score_error:
                    print(f"Langfuse score error: {score_error}")

            return JSONResponse(status_code=500, content={"error": str(e)})
    except Exception as e:
        # Handle the case where request.json() fails
        if trace:
            try:
                trace.score(
                    name="error",
                    value=0,
                    comment=f"Request parsing error: {str(e)}"
                )
            except Exception as score_error:
                print(f"Langfuse score error: {score_error}")

        return JSONResponse(status_code=500, content={"error": str(e)})

    # Ollama expects a streaming-like text block in one chunk
    response_content = {
        "model": model,  # Return the original model name (with tag) to maintain consistency
        "created_at": "",
        "response": content,
        "done": True
    }

    # Update trace with output if tracing is active
    if trace:
        try:
            trace.update(output=response_content)
        except Exception as e:
            print(f"Langfuse trace update error: {e}")

    return JSONResponse(content=response_content)

@app.get("/api/version")
async def version():
    response_content = {"version": "1.0.0"}

    # Add LangFuse trace if available and should sample (for high-frequency endpoints)
    if LANGFUSE_AVAILABLE and langfuse and should_sample_endpoint():
        try:
            trace = langfuse.start_span(
                name="api-version",
                input={"endpoint": "/api/version"},
                metadata={"endpoint": "/api/version", "service": "bitnet-proxy"}
            )
            trace.update(output=response_content)
        except Exception as e:
            print(f"Langfuse error in /api/version: {e}")

    return response_content

@app.get("/ollama/api/version")
async def ollama_version():
    response_content = {"version": "1.0.0"}

    # Add LangFuse trace if available and should sample (for high-frequency endpoints)
    if LANGFUSE_AVAILABLE and langfuse and should_sample_endpoint():
        try:
            trace = langfuse.start_span(
                name="ollama-api-version",
                input={"endpoint": "/ollama/api/version"},
                metadata={"endpoint": "/ollama/api/version", "service": "bitnet-proxy"}
            )
            trace.update(output=response_content)
        except Exception as e:
            print(f"Langfuse error in /ollama/api/version: {e}")

    return response_content

@app.get("/api/models")
async def models_openai():
    """OpenAI-style endpoint for models listing."""
    trace = None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{BITNET_BASE_URL}/v1/models")
            r.raise_for_status()
            data = r.json()
        out = []
        for m in data.get("data", []):
            mid = m.get("id") or m.get("name", "unknown-model")
            # Ensure the model ID is in a format that Open WebUI expects
            # Similar to /v1/models endpoint for consistency
            if "bitnet" in mid.lower():
                # Create a simplified ID for Open WebUI compatibility
                simplified_id = "bitnet-b158-2b"
            else:
                simplified_id = mid
            out.append({
                "model": simplified_id,  # Changed from "id" to "model" for Ollama compatibility
                "name": simplified_id,   # Add the name field for compatibility
                "id": simplified_id,
                "object": "model",
                "owned_by": "bitnet",
                "created": m.get("created", 1762832050),
            })
        response_content = {"data": out, "object": "list"}
    except Exception as e:
        response_content = {"data": [{"model": "bitnet-b158-2b", "name": "bitnet-b158-2b", "id": "bitnet-b158-2b", "object": "model", "owned_by": "bitnet", "created": 1762832050}], "object": "list"}

    # Add LangFuse trace if available and should sample (for high-frequency endpoints)
    if LANGFUSE_AVAILABLE and langfuse and should_sample_endpoint():
        try:
            trace = langfuse.start_span(
                name="api-models",
                input={"endpoint": "/api/models"},
                metadata={"endpoint": "/api/models", "service": "bitnet-proxy"}
            )

            if response_content:
                trace.update(output=response_content)

            if 'e' in locals():  # If there was an exception
                trace.score(
                    name="error",
                    value=0,
                    comment=f"Exception: {str(e)}"
                )
        except Exception as trace_error:
            print(f"Langfuse error in /api/models: {trace_error}")

    return response_content

# NEW: OpenAI-compatible endpoints for Open WebUI compatibility
@app.get("/v1/models")
async def openai_models():
    """OpenAI-compatible models endpoint."""
    trace = None

    try:
        # Connect to the BitNet backend directly
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{BITNET_BASE_URL}/v1/models")
            r.raise_for_status()
            data = r.json()

        # Return OpenAI-compatible listing
        out = []
        for m in data.get("data", []):
            mid = m.get("id") or m.get("name", "unknown-model")
            # Ensure the model ID is in a format that Open WebUI expects
            # Replace problematic characters for version parsing
            if "bitnet" in mid.lower():
                # Create a simplified ID for Open WebUI compatibility
                simplified_id = "bitnet-b158-2b"
            else:
                simplified_id = mid
            out.append({
                "id": simplified_id,
                "model": simplified_id,  # Add the model field for compatibility
                "name": simplified_id,   # Add the name field for Open WebUI compatibility
                "object": "model",
                "owned_by": "bitnet",
                "created": m.get("created", 1762832050)
            })
        response_content = {"data": out, "object": "list"}
    except Exception as e:
        # Fallback if BitNet server is unavailable
        response_content = {
            "data": [{
                "id": "bitnet-b158-2b",
                "model": "bitnet-b158-2b",  # Add the model field for Open WebUI compatibility
                "name": "bitnet-b158-2b",   # Add the name field for Open WebUI compatibility
                "object": "model",
                "owned_by": "bitnet",
                "created": 1762832050
            }],
            "object": "list"
        }

    # Add LangFuse trace if available and should sample (for high-frequency endpoints)
    if LANGFUSE_AVAILABLE and langfuse and should_sample_endpoint():
        try:
            trace = langfuse.start_span(
                name="openai-models",
                input={"endpoint": "/v1/models"},
                metadata={"endpoint": "/v1/models", "service": "bitnet-proxy"}
            )

            if response_content:
                trace.update(output=response_content)

            if 'e' in locals():  # If there was an exception
                trace.score(
                    name="error",
                    value=0,
                    comment=f"Exception: {str(e)}"
                )
        except Exception as trace_error:
            print(f"Langfuse error in /v1/models: {trace_error}")

    return response_content

@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint."""
    trace = None
    generation = None

    try:
        data = await request.json()
        model = data.get("model", "bitnet-b158-2b")
        # Handle model names with tags (like "model:latest") by extracting just the base name
        base_model = model.split(':')[0] if ':' in model else model
        messages = data.get("messages", [])
        payload = {
            "model": base_model,  # Use the base model name without tag for BitNet
            "messages": messages,
            "max_tokens": data.get("max_tokens", 256),
            "temperature": data.get("temperature", 0.7),
        }

        # Add LangFuse trace if available
        if LANGFUSE_AVAILABLE and langfuse:
            try:
                trace = langfuse.start_span(
                    name="openai-chat-completions",
                    input=data,
                    metadata={"endpoint": "/v1/chat/completions", "service": "bitnet-proxy"}
                )

                # Create a generation trace for the actual model call (using start_observation)
                try:
                    generation = langfuse.start_observation(
                        trace_context={"trace_id": trace.trace_id},  # Link to the parent span's trace
                        name="bitnet-generation",
                        as_type="generation",
                        input=payload,
                        model=base_model,
                    )
                except Exception as gen_error:
                    print(f"Langfuse generation linking error: {gen_error}. Creating unlinked generation.")
                    # If trace_id approach fails, create generation without linking to trace
                    generation = langfuse.start_observation(
                        name="bitnet-generation",
                        as_type="generation",
                        input=payload,
                        model=base_model,
                    )
            except Exception as e:
                print(f"Langfuse error in /v1/chat/completions trace setup: {e}")

        try:
            # Call BitNet backend
            async with httpx.AsyncClient(timeout=600) as client:
                r = await client.post(BITNET_URL, json=payload)
                r.raise_for_status()
                response_data = r.json()

            content = response_data["choices"][0]["message"]["content"]

            # Update the generation with output if tracing is active
            if generation:
                try:
                    generation.update(output={"content": content})
                    generation.end()
                except Exception as e:
                    # If update and end fail, just try to end the generation
                    try:
                        generation.end()
                    except Exception as e2:
                        print(f"Langfuse generation end error: {e}, fallback error: {e2}")

            if data.get("stream", False):
                # For streaming, return StreamingResponse
                def generate():
                    chunk = {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,  # Return the original model name (with tag) to maintain consistency
                        "choices": [{
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    yield "data: [DONE]\n\n"

                return StreamingResponse(generate(), media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})
            else:
                # Return standard OpenAI format response
                response_content = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,  # Return the original model name (with tag) to maintain consistency
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "finish_reason": "stop"
                    }],
                }

                # Update trace with output if tracing is active
                if trace:
                    try:
                        trace.update(output=response_content)
                    except Exception as e:
                        print(f"Langfuse trace update error: {e}")

                return response_content
        except httpx.HTTPStatusError as e:
            # Log the error to LangFuse if available
            if trace:
                try:
                    trace.score(
                        name="error",
                        value=0,
                        comment=f"HTTP error: {e.response.status_code}"
                    )
                except Exception as score_error:
                    print(f"Langfuse score error: {score_error}")
            return JSONResponse(status_code=e.response.status_code, content=e.response.json())
        except Exception as e:
            # Log the error to LangFuse if available
            if trace:
                try:
                    trace.score(
                        name="error",
                        value=0,
                        comment=f"Exception: {str(e)}"
                    )
                except Exception as score_error:
                    print(f"Langfuse score error: {score_error}")
            return JSONResponse(status_code=500, content={"error": str(e)})
    except Exception as e:
        # Handle the case where request.json() fails
        if trace:
            try:
                trace.score(
                    name="error",
                    value=0,
                    comment=f"Request parsing error: {str(e)}"
                )
            except Exception as score_error:
                print(f"Langfuse score error: {score_error}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Optional: Add completions endpoint for text completion
@app.post("/v1/completions")
async def openai_completions(request: Request):
    """OpenAI-compatible completions endpoint."""
    trace = None
    generation = None

    try:
        data = await request.json()
        model = data.get("model", "bitnet-b158-2b")
        # Handle model names with tags (like "model:latest") by extracting just the base name
        base_model = model.split(':')[0] if ':' in model else model
        prompt = data.get("prompt", "")
        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": base_model,  # Use the base model name without tag for BitNet
            "messages": messages,
            "max_tokens": data.get("max_tokens", 256),
            "temperature": data.get("temperature", 0.7),
        }

        # Add LangFuse trace if available
        if LANGFUSE_AVAILABLE and langfuse:
            try:
                trace = langfuse.start_span(
                    name="openai-completions",
                    input=data,
                    metadata={"endpoint": "/v1/completions", "service": "bitnet-proxy"}
                )

                # Create a generation trace for the actual model call (using start_observation)
                try:
                    generation = langfuse.start_observation(
                        trace_context={"trace_id": trace.trace_id},  # Link to the parent span's trace
                        name="bitnet-generation",
                        as_type="generation",
                        input=payload,
                        model=base_model,
                    )
                except Exception as gen_error:
                    print(f"Langfuse generation linking error: {gen_error}. Creating unlinked generation.")
                    # If trace_id approach fails, create generation without linking to trace
                    generation = langfuse.start_observation(
                        name="bitnet-generation",
                        as_type="generation",
                        input=payload,
                        model=base_model,
                    )
            except Exception as e:
                print(f"Langfuse error in /v1/completions trace setup: {e}")

        try:
            async with httpx.AsyncClient(timeout=600) as client:
                r = await client.post(BITNET_URL, json=payload)
                r.raise_for_status()
                response_data = r.json()

            content = response_data["choices"][0]["message"]["content"]

            # Update the generation with output if tracing is active
            if generation:
                try:
                    generation.update(output={"content": content})
                    generation.end()
                except Exception as e:
                    # If update and end fail, just try to end the generation
                    try:
                        generation.end()
                    except Exception as e2:
                        print(f"Langfuse generation end error: {e}, fallback error: {e2}")

            if data.get("stream", False):
                def generate():
                    chunk = {
                        "id": f"cmpl-{int(time.time())}",
                        "object": "text_completion.chunk",
                        "created": int(time.time()),
                        "model": model,  # Return the original model name (with tag) to maintain consistency
                        "choices": [{
                            "text": content,
                            "index": 0,
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    yield "data: [DONE]\n\n"

                return StreamingResponse(generate(), media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})
            else:
                response_content = {
                    "id": f"cmpl-{int(time.time())}",
                    "object": "text_completion",
                    "created": int(time.time()),
                    "model": model,  # Return the original model name (with tag) to maintain consistency
                    "choices": [{
                        "text": content,
                        "index": 0,
                        "finish_reason": "stop"
                    }],
                }

                # Update trace with output if tracing is active
                if trace:
                    try:
                        trace.update(output=response_content)
                    except Exception as e:
                        print(f"Langfuse trace update error: {e}")

                return response_content
        except httpx.HTTPStatusError as e:
            # Log the error to LangFuse if available
            if trace:
                try:
                    trace.score(
                        name="error",
                        value=0,
                        comment=f"HTTP error: {e.response.status_code}"
                    )
                except Exception as score_error:
                    print(f"Langfuse score error: {score_error}")
            return JSONResponse(status_code=e.response.status_code, content=e.response.json())
        except Exception as e:
            # Log the error to LangFuse if available
            if trace:
                try:
                    trace.score(
                        name="error",
                        value=0,
                        comment=f"Exception: {str(e)}"
                    )
                except Exception as score_error:
                    print(f"Langfuse score error: {score_error}")
            return JSONResponse(status_code=500, content={"error": str(e)})
    except Exception as e:
        # Handle the case where request.json() fails
        if trace:
            try:
                trace.score(
                    name="error",
                    value=0,
                    comment=f"Request parsing error: {str(e)}"
                )
            except Exception as score_error:
                print(f"Langfuse score error: {score_error}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Properly close LangFuse client on application shutdown
@app.on_event("shutdown")
async def shutdown_event():
    if LANGFUSE_AVAILABLE and langfuse:
        try:
            langfuse.flush()
        except Exception as e:
            print(f"Langfuse flush error during shutdown: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)