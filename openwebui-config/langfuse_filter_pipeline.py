"""
title: Langfuse Forwarding Pipeline
author: open-webui
date: 2025-06-16
version: 2.0.0
license: MIT
description: A pipeline that forwards requests to backend while tracing to Langfuse.
requirements: langfuse<3.0.0, httpx
"""

from typing import List, Optional, Dict, Any, Union
import os
import uuid
import json
import httpx

from pydantic import BaseModel
from langfuse import Langfuse
from langfuse.api.resources.commons.errors.unauthorized_error import UnauthorizedError


class Pipeline:
    class Valves(BaseModel):
        pipelines: List[str] = []
        priority: int = 0
        secret_key: str
        public_key: str
        host: str
        upstream_base_url: str  # Where to forward requests
        timeout: float = 300.0
        debug: bool = False

    def __init__(self):
        self.type = "filter"
        self.id = "langfuse_forwarding_pipeline"
        self.name = "Langfuse Forwarding Pipeline"

        self.valves = self.Valves(
            pipelines=["*"],
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-03f98e68-54ea-424b-af23-3acb63f06001"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-c744a3d3-6166-43d5-a578-7bead547d4ea"),
            host=os.getenv("LANGFUSE_HOST", "http://host.docker.internal:3001"),
            upstream_base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:8001"),
            timeout=float(os.getenv("UPSTREAM_TIMEOUT", "300")),
            debug=os.getenv("DEBUG_MODE", "false").lower() == "true",
        )

        self.langfuse = None
        self.chat_traces = {}
        self.model_names = {}
        
        # Initialize Langfuse
        self.set_langfuse()

    def log(self, message: str):
        if self.valves.debug:
            print(f"[DEBUG-LANGFUSE-FWD] {message}")

    async def on_startup(self):
        self.log(f"On startup triggered for {__name__}")
        self.set_langfuse()

    async def on_shutdown(self):
        self.log(f"On shutdown triggered for {__name__}")
        if self.langfuse:
            self.langfuse.flush()

    async def on_valves_updated(self):
        self.log("Valves updated, resetting Langfuse client.")
        self.set_langfuse()

    def set_langfuse(self):
        try:
            self.langfuse = Langfuse(
                secret_key=self.valves.secret_key,
                public_key=self.valves.public_key,
                host=self.valves.host,
                debug=self.valves.debug,
            )
            self.langfuse.auth_check()
            self.log("Langfuse client initialized successfully.")
        except UnauthorizedError:
            print("Langfuse credentials incorrect. Please check pipeline settings.")
        except Exception as e:
            print(f"Langfuse error: {e}")

    def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """
        Intercept incoming request and create Langfuse trace
        """
        self.log(f"Inlet called with body keys: {list(body.keys())}")
        
        # Generate trace ID for this request
        trace_id = str(uuid.uuid4())
        
        # Determine API path based on request content
        if "/models" in str(body).lower():
            api_path = "/models"
        elif "messages" in body and len(body.get("messages", [])) > 0:
            api_path = "/chat/completions"
        elif "prompt" in body:
            api_path = "/completions"
        else:
            api_path = "/chat/completions"  # default

        # Start Langfuse trace
        if self.langfuse:
            trace = self.langfuse.trace(
                id=trace_id,
                name=f"bitnet_request_{api_path.replace('/', '_')}",
                metadata={
                    "model": body.get("model", "unknown"),
                    "user": user.get("name", "unknown") if user else "unknown",
                    "api_path": api_path,
                    "upstream": self.valves.upstream_base_url
                },
                input=body
            )
            
            # Store trace for use in outlet
            self.chat_traces[trace_id] = trace
            
            # Add trace_id to body so we can retrieve it in outlet
            body["__trace_id__"] = trace_id
        
        self.log(f"Started trace {trace_id} for path {api_path}")
        return body

    def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """
        Intercept outgoing response and complete Langfuse trace
        """
        self.log(f"Outlet called with body keys: {list(body.keys())}")
        
        # Retrieve trace ID
        trace_id = body.pop("__trace_id__", None)
        
        if trace_id and trace_id in self.chat_traces:
            trace = self.chat_traces[trace_id]
            
            # Complete the trace with response
            if self.langfuse:
                trace.update(
                    output=body,
                    metadata={
                        "response_type": "standard",
                        "model_used": body.get("model", "unknown")
                    }
                )
                
                # Clean up trace reference
                del self.chat_traces[trace_id]
                self.log(f"Completed trace {trace_id}")
        
        return body