from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.responses import Response
import httpx
import asyncio
import json
from langfuse import Langfuse
import os

# Load environment variables from .env file
load_dotenv()

# Global LangFuse client (singleton pattern)
langfuse_client = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
    host=os.getenv("LANGFUSE_HOST", "http://localhost:3001"),
    debug=False  # Set to True for debugging, False for production
)

app = FastAPI()

# Target API configuration (your BitNet proxy)
TARGET_API_URL = os.getenv("TARGET_API_URL", "http://localhost:8000")  # Points to actual BitNet server

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(request: Request, path: str):
    """Proxy all requests to the target API while adding LangFuse tracing"""

    # Use the global LangFuse client - declare global at the beginning
    global langfuse_client

    # Full URL to forward to
    target_url = f"{TARGET_API_URL}/{path}"

    # Get request data
    body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else b""

    # Prepare headers
    headers = dict(request.headers)
    headers.pop("host", None)  # Remove original host header

    # Debug: Check if LangFuse client is properly initialized and keys are loaded
    print(f"LANGFUSE_CLIENT_INITIALIZED: {langfuse_client is not None}")
    print(f"PUBLIC_KEY_LAST_4: {os.getenv('LANGFUSE_PUBLIC_KEY', '')[-4:]}")
    print(f"SECRET_KEY_LAST_4: {os.getenv('LANGFUSE_SECRET_KEY', '')[-4:]}")
    print(f"LANGFUSE_HOST: {os.getenv('LANGFUSE_HOST', 'http://localhost:3001')}")
    print(f"TARGET_URL: {target_url}")
    print(f"PATH: {path}")
    print(f"METHOD: {request.method}")

    # Create LangFuse trace - first create a span which will be the root of the trace
    try:
        span = langfuse_client.start_span(
            name=f"webui-{path}",
            input={
                "url": target_url,
                "method": request.method,
                "headers": headers,
                "body": json.loads(body.decode()) if body else None
            },
            metadata={
                "source": "open-webui",
                "path": path
            }
        )
        print(f"LANGFUSE_SPAN_CREATED: {span is not None}, trace_id: {span.trace_id}")
    except Exception as e:
        print(f"LANGFUSE_ERROR_CREATING_SPAN: {e}")
        # Continue with the request even if LangFuse fails
        span = None

    # Continue processing regardless of LangFuse success

    try:
        async with httpx.AsyncClient(timeout=600) as client:
            # Make the request to the target API
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )

            # Capture the response in LangFuse if span was created successfully
            response_content = response.content
            if span is not None and response_content:  # Only process if span exists
                try:
                    response_json = response.json()
                    # Create a generation as a child of the span
                    generation = langfuse_client.start_observation(
                        trace_context={"trace_id": span.trace_id},  # Link to the parent span's trace
                        name="llm-generation",
                        as_type="generation",
                        input=json.loads(body.decode()) if body else {},
                        output=response_json,
                        model=response_json.get("model", "unknown")
                    )
                    generation.end()
                    print(f"LANGFUSE_GENERATION_CREATED: trace_id={span.trace_id}")
                except Exception as gen_error:
                    print(f"LANGFUSE_ERROR_CREATING_GENERATION: {gen_error}")
                    # Create generation with basic data if JSON parsing fails
                    generation = langfuse_client.start_observation(
                        trace_context={"trace_id": span.trace_id},  # Link to the parent span's trace
                        name="llm-generation",
                        as_type="generation",
                        input=json.loads(body.decode()) if body else {},
                        output=response.text,
                        model="unknown"
                    )
                    generation.end()

            if span is not None:  # Only update if span exists
                # Update the root span with output
                span.update(output=response.json() if response_content else response.text)
                print(f"LANGFUSE_SPAN_UPDATED: trace_id={span.trace_id}")

            # Return the target response
            return Response(
                content=response_content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )

    except Exception as e:
        # Log error in LangFuse (using the global client that's already in scope)
        print(f"Error occurred in request processing: {e}")
        try:
            error_span = langfuse_client.start_span(
                name=f"error-{path}",
                input={"url": target_url, "method": request.method},
                output={"error": str(e)},
                level="ERROR"
            )
            error_span.end()
            print(f"LANGFUSE_ERROR_SPAN_CREATED: trace_id={error_span.trace_id}")
        except Exception as span_error:
            print(f"LANGFUSE_ERROR_CREATING_ERROR_SPAN: {span_error}")
        raise e

    # Finally block for successful requests
    finally:
        # End the root span if it was created and flush the global client to ensure data is sent to LangFuse
        if 'span' in locals() and span is not None:
            try:
                span.end()
                print(f"LANGFUSE_SPAN_ENDED: trace_id={span.trace_id}")
            except Exception as span_end_error:
                print(f"LANGFUSE_ERROR_ENDING_SPAN: {span_end_error}")

        # Always flush to ensure any pending data is sent to LangFuse
        try:
            langfuse_client.flush()
            print("LANGFUSE_CLIENT_FLUSHED: Data sent to LangFuse")
        except Exception as flush_error:
            print(f"LANGFUSE_ERROR_FLUSHING: {flush_error}")

@app.get("/")
async def root():
    return {"message": "LangFuse-WebUI Integration Proxy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3004)  # Using port 3004 to avoid conflicts