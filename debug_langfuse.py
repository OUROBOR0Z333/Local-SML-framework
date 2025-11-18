#!/usr/bin/env python3
"""
LangFuse Debugging Tool
This script tests the connectivity and tracing functionality of your LangFuse setup.
"""

import os
import asyncio
import httpx
from datetime import datetime, timedelta
import json

from langfuse import Langfuse


def test_langfuse_connectivity():
    """Test basic connectivity to LangFuse instance"""
    print("=== Testing LangFuse Connectivity ===")
    
    # Get environment variables
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3001")
    
    if not public_key or not secret_key:
        print("❌ ERROR: LANGFUSE_PUBLIC_KEY and/or LANGFUSE_SECRET_KEY not set in environment")
        print("   Please set the environment variables before running this test")
        return False
    
    print(f"Using LangFuse host: {host}")
    print(f"Public key: {public_key[:8]}... (truncated)")
    print(f"Secret key: {secret_key[:8]}... (truncated)")
    
    try:
        # Test basic HTTP connectivity
        print(f"\n1. Testing HTTP connectivity to {host}/api/public/health...")
        response = httpx.get(f"{host}/api/public/health", timeout=10.0)
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ HTTP connection successful: {health_data}")
        else:
            print(f"   ❌ HTTP connection failed: Status {response.status_code}")
            return False
        
        # Test LangFuse client initialization
        print(f"\n2. Testing LangFuse client initialization...")
        langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            debug=True  # Enable debug output
        )
        print(f"   ✅ LangFuse client initialized successfully")
        
        # Check required methods
        required_methods = ['start_span', 'start_observation']
        missing_methods = [method for method in required_methods if not hasattr(langfuse, method)]
        if missing_methods:
            print(f"   ❌ Missing required methods: {missing_methods}")
            return False
        else:
            print(f"   ✅ All required methods available: {required_methods}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error during connectivity test: {e}")
        return False


def test_trace_creation():
    """Test actual trace creation and submission to LangFuse"""
    print("\n=== Testing Trace Creation ===")
    
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3001")
    
    try:
        print("1. Creating a test trace...")
        langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            debug=True
        )
        
        # Create a test span
        test_span = langfuse.start_span(
            name="debug-test-span",
            input={"test": "This is a debug test"},
            metadata={"service": "debug-tool", "timestamp": datetime.now().isoformat()}
        )
        
        print(f"   ✅ Test span created: {test_span}")
        
        # Create a linked generation (observation)
        try:
            test_generation = langfuse.start_observation(
                trace_context={"trace_id": test_span.trace_id},
                name="debug-test-generation",
                as_type="generation",
                input={"prompt": "Debug test prompt"},
                output={"content": "Debug test response"},
                model="debug-model"
            )
            print(f"   ✅ Linked generation created with trace_id: {test_span.trace_id}")
        except Exception as gen_error:
            print(f"   ⚠️  Error creating linked generation: {gen_error}")
            print(f"   ℹ️  Creating unlinked generation as fallback...")
            test_generation = langfuse.start_observation(
                name="debug-test-generation",
                as_type="generation",
                input={"prompt": "Debug test prompt"},
                output={"content": "Debug test response"},
                model="debug-model"
            )
            print(f"   ✅ Unlinked generation created")
        
        # Update and end the generation
        if test_generation:
            try:
                test_generation.update(output={"content": "Updated debug response", "tokens": 10})
                test_generation.end()
                print(f"   ✅ Generation updated and ended")
            except Exception as e:
                print(f"   ⚠️  Error updating generation: {e}")
                test_generation.end()  # Try ending without update
                print(f"   ✅ Generation ended")
        
        # Update and end the span
        try:
            test_span.update(output={"result": "Debug test completed successfully"})
            test_span.end()
            print(f"   ✅ Test span updated and ended")
        except Exception as e:
            print(f"   ⚠️  Error updating span: {e}")
            test_span.end()  # Try ending without update
            print(f"   ✅ Test span ended")
        
        # Force flush to send immediately
        print("2. Flushing traces to LangFuse...")
        langfuse.flush()
        print("   ✅ Traces flushed")
        
        print("   ℹ️  Note: Check your LangFuse UI for the 'debug-test-span' trace")
        print("   ℹ️  It may take a few seconds to appear in the dashboard")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error during trace creation test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_proxy_endpoints():
    """Test the proxy endpoints to ensure they're working and tracing"""
    print("\n=== Testing Proxy Endpoints ===")
    
    proxy_url = "http://localhost:8001"
    
    try:
        # Test models endpoint
        print("1. Testing /v1/models endpoint...")
        response = httpx.get(f"{proxy_url}/v1/models", timeout=10.0)
        if response.status_code == 200:
            print(f"   ✅ /v1/models: {response.status_code}")
        else:
            print(f"   ❌ /v1/models: {response.status_code} - {response.text}")
            return False
        
        # Test a simple chat completion to trigger tracing
        print("2. Testing /v1/chat/completions endpoint (this will trigger tracing)...")
        test_payload = {
            "model": "bitnet-b158-2b",  # This will fail at the backend but should still be traced
            "messages": [
                {"role": "user", "content": "This is a debug test - just checking tracing"}
            ],
            "temperature": 0.7,
            "max_tokens": 20
        }
        
        # Don't expect this to work if BitNet backend isn't running, 
        # but it should still create traces in the proxy
        try:
            response = httpx.post(
                f"{proxy_url}/v1/chat/completions",
                json=test_payload,
                timeout=30.0
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ /v1/chat/completions: Success - response received")
            else:
                print(f"   ⚠️  /v1/chat/completions: {response.status_code}")
                print(f"      Response: {response.text[:200]}...")
        except httpx.TimeoutException:
            print("   ⚠️  /v1/chat/completions: Request timed out (expected if backend is not running)")
        except Exception as e:
            print(f"   ⚠️  /v1/chat/completions: Error - {e}")
        
        print("   ℹ️  Check your LangFuse UI for traces from these requests")
        print("   ℹ️  Look for traces named 'openai-chat-completions', 'api-models', etc.")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error during proxy testing: {e}")
        return False


def main():
    print("LangFuse Debugging Tool")
    print("="*50)
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Connectivity Test", test_langfuse_connectivity),
        ("Trace Creation Test", test_trace_creation),
        ("Proxy Endpoint Test", test_proxy_endpoints)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        result = test_func()
        results[test_name] = result
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"\n{test_name}: {status}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY:")
    all_passed = all(results.values())
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall Status: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if not all_passed:
        print(f"\nTROUBLESHOOTING TIPS:")
        print(f"  1. Ensure LangFuse is running on {os.getenv('LANGFUSE_HOST', 'http://localhost:3001')}")
        print(f"  2. Verify your API keys are correct")
        print(f"  3. Check that environment variables are set:")
        print(f"     - LANGFUSE_PUBLIC_KEY")
        print(f"     - LANGFUSE_SECRET_KEY") 
        print(f"     - LANGFUSE_HOST")
        print(f"  4. Make sure the proxy (port 8001) is running")
        print(f"  5. Wait 30-60 seconds after requests before checking LangFuse UI")


if __name__ == "__main__":
    main()