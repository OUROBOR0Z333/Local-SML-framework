#!/usr/bin/env python3
"""
Test script to verify LangFuse tracing in the BitNet proxy
"""
import asyncio
import os
import sys
from bitnet_ollama_proxy import app
import uvicorn

if __name__ == "__main__":
    # Set environment variables
    os.environ['LANGFUSE_PUBLIC_KEY'] = 'pk-lf-9dc915a9-0d54-48fb-ba35-c2d18baac3ba'
    os.environ['LANGFUSE_SECRET_KEY'] = 'sk-lf-7864c537-79ba-4e28-a87f-3f19f88bfd27'
    os.environ['LANGFUSE_HOST'] = 'http://localhost:3001'
    
    print("Starting proxy with LangFuse tracing enabled...")
    print("Make requests to http://localhost:8001 to test tracing")
    print("Check LangFuse UI at http://localhost:3001 for traces")
    
    # Run the proxy
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="debug",
        access_log=True
    )