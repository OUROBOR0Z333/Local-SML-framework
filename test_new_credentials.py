#!/usr/bin/env python3
"""
Test script using the new LangFuse credentials to verify they work
"""

import os
import time
import uuid
from datetime import datetime, timezone

# Use the new credentials provided
LF_PUBLIC = "pk-lf-82f9b2b9-c15f-4883-b1f9-d28179337ab1"
LF_SECRET = "sk-lf-436c105d-12f6-47db-967b-db4629585688"
LF_HOST = "http://localhost:3001"

def test_credentials():
    try:
        from langfuse import Langfuse
    except ImportError:
        print("❌  'langfuse' package missing →  pip install langfuse")
        return False

    # Create a simple trace
    print("Creating a test trace with new credentials...")
    lf = Langfuse(
        public_key=LF_PUBLIC,
        secret_key=LF_SECRET,
        host=LF_HOST,
        debug=True  # Enable debug to see what's happening
    )

    span_name = f"test-span-{uuid.uuid4().hex[:8]}"
    test_attr = {"ping": "pong", "ts": datetime.now(timezone.utc).isoformat()}

    try:
        span = lf.start_span(name=span_name, input=test_attr)
        span.update(output={"status": "ok"})
        span.end()
        print(f"✅  Created span '{span_name}' successfully")
        
        # Try to flush immediately
        lf.flush()
        print("✅  Flushed traces to LangFuse")
        return True
    except Exception as e:
        print(f"❌  Error creating trace: {e}")
        return False

if __name__ == "__main__":
    test_credentials()