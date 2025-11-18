#!/usr/bin/env python3
"""
Quick test to verify LangFuse is working with proxy credentials
"""
import os
from dotenv import load_dotenv
from langfuse import Langfuse

# Load environment variables
load_dotenv()

# Get credentials from environment
public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
secret_key = os.getenv("LANGFUSE_SECRET_KEY")
host = os.getenv("LANGFUSE_HOST", "http://localhost:3001")

print(f"Using credentials:")
print(f"Public Key: {public_key}")
print(f"Host: {host}")

try:
    # Initialize Langfuse client
    langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
        debug=True
    )
    
    # Verify the connection
    langfuse.auth_check()
    print("✅ Langfuse authentication successful!")
    
    # Create a test trace
    trace = langfuse.trace(
        name="proxy-connection-test",
        input={"test": "connection"},
        metadata={"service": "bitnet-proxy-test"}
    )
    
    print(f"✅ Trace created with ID: {trace.id}")
    
    # Update and end the trace
    trace.update(output={"result": "success"})
    
    # Flush to ensure it's sent
    langfuse.flush()
    print("✅ Trace sent to Langfuse successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()