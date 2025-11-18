#!/usr/bin/env python3
"""
Test script to verify that we can manually create traces using the same 
approach as the proxy using the working credentials
"""

import os
import time
import uuid
from langfuse import Langfuse

# Use the working credentials
LANGFUSE_PUBLIC_KEY = "pk-lf-c744a3d3-6166-43d5-a578-7bead547d4ea"
LANGFUSE_SECRET_KEY = "sk-lf-03f98e68-54ea-424b-af23-3acb63f06001"
LANGFUSE_HOST = "http://localhost:3001"

def test_manual_trace():
    print("Testing manual trace creation with working credentials...")
    
    try:
        # Initialize LangFuse client as the proxy does
        langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
            debug=True  # Enable debug to see what's happening
        )
        
        print("✓ LangFuse client initialized successfully")
        
        # Create a test span like the proxy does
        span_name = f"manual-test-span-{uuid.uuid4().hex[:8]}"
        print(f"Creating span: {span_name}")
        
        trace = langfuse.start_span(
            name=span_name,
            input={"test": "This is a manual test trace from BitNet proxy equivalent"},
            metadata={"service": "bitnet-proxy-test", "endpoint": "/api/test"}
        )
        
        print("✓ Span created successfully")
        
        # Update with output like the proxy does
        trace.update(output={"result": "success", "message": "Trace created manually"})
        print("✓ Span output updated")
        
        # End the span like the proxy does
        trace.end()
        print("✓ Span ended")
        
        # Flush to ensure it's sent like the proxy does on shutdown
        langfuse.flush()
        print("✓ Flushed to LangFuse")
        
        print(f"Manual test completed. Check LangFuse UI for span: {span_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error in manual trace test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_manual_trace()