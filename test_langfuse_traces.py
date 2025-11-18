#!/usr/bin/env python3
"""
Diagnostic script to trigger traces and verify LangFuse is working.
Tests all endpoints of the BitNet AI Gateway proxy.
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
PROXY_URL = "http://localhost:8001"
LANGFUSE_UI = "http://localhost:3001"

# LangFuse API credentials (from your .env)
LANGFUSE_PUBLIC_KEY = "pk-lf-9dc915a9-0d54-48fb-ba35-c2d18baac3ba"
LANGFUSE_SECRET_KEY = "sk-lf-7864c537-79ba-4e28-a87f-3f19f88bfd27"
LANGFUSE_HOST = "http://localhost:3001"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def log_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def log_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")

def log_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")

def check_proxy_health():
    """Check if proxy is running"""
    log_info("Checking proxy health...")
    try:
        response = requests.get(f"{PROXY_URL}/api/version", timeout=5)
        if response.status_code == 200:
            log_success(f"Proxy is running: {response.json()}")
            return True
        else:
            log_error(f"Proxy returned status {response.status_code}")
            return False
    except Exception as e:
        log_error(f"Cannot reach proxy: {e}")
        return False

def check_langfuse_health():
    """Check if LangFuse is running"""
    log_info("Checking LangFuse health...")
    try:
        response = requests.get(f"{LANGFUSE_HOST}/api/public/health", timeout=5)
        if response.status_code == 200:
            log_success(f"LangFuse is running")
            return True
        else:
            log_error(f"LangFuse returned status {response.status_code}")
            return False
    except Exception as e:
        log_error(f"Cannot reach LangFuse: {e}")
        return False

def trigger_trace_api_tags():
    """Test /api/tags endpoint"""
    log_info("Triggering trace: GET /api/tags")
    try:
        response = requests.get(f"{PROXY_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            log_success(f"GET /api/tags succeeded - trace should be created")
            print(f"  Response: {json.dumps(response.json(), indent=2)[:200]}...")
            return True
        else:
            log_error(f"GET /api/tags failed with status {response.status_code}")
            return False
    except Exception as e:
        log_error(f"GET /api/tags error: {e}")
        return False

def trigger_trace_generate():
    """Test /api/generate endpoint (Ollama format)"""
    log_info("Triggering trace: POST /api/generate")
    payload = {
        "model": "bitnet",
        "prompt": "What is 2+2?",
        "stream": False
    }
    try:
        response = requests.post(
            f"{PROXY_URL}/api/generate",
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            log_success(f"POST /api/generate succeeded - trace should be created")
            print(f"  Response preview: {str(response.json())[:200]}...")
            return True
        else:
            log_error(f"POST /api/generate failed with status {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        log_error(f"POST /api/generate error: {e}")
        return False

def trigger_trace_openai_models():
    """Test /v1/models endpoint (OpenAI format)"""
    log_info("Triggering trace: GET /v1/models")
    try:
        response = requests.get(f"{PROXY_URL}/v1/models", timeout=10)
        if response.status_code == 200:
            log_success(f"GET /v1/models succeeded - trace should be created")
            print(f"  Response: {json.dumps(response.json(), indent=2)[:200]}...")
            return True
        else:
            log_error(f"GET /v1/models failed with status {response.status_code}")
            return False
    except Exception as e:
        log_error(f"GET /v1/models error: {e}")
        return False

def trigger_trace_openai_chat():
    """Test /v1/chat/completions endpoint (OpenAI format)"""
    log_info("Triggering trace: POST /v1/chat/completions")
    payload = {
        "model": "bitnet",
        "messages": [
            {"role": "user", "content": "Say hello!"}
        ],
        "stream": False
    }
    try:
        response = requests.post(
            f"{PROXY_URL}/v1/chat/completions",
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            log_success(f"POST /v1/chat/completions succeeded - trace should be created")
            print(f"  Response preview: {str(response.json())[:200]}...")
            return True
        else:
            log_error(f"POST /v1/chat/completions failed with status {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        log_error(f"POST /v1/chat/completions error: {e}")
        return False

def check_langfuse_traces():
    """Query LangFuse API to check if traces were received"""
    log_info("Querying LangFuse for recent traces...")
    
    # Wait a moment for traces to be indexed
    time.sleep(2)
    
    try:
        # Query LangFuse API directly
        response = requests.get(
            f"{LANGFUSE_HOST}/api/public/traces",
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            timeout=10,
            params={"limit": 10}
        )
        
        if response.status_code == 200:
            data = response.json()
            trace_count = len(data.get("data", []))
            
            if trace_count > 0:
                log_success(f"Found {trace_count} traces in LangFuse!")
                print("\nRecent traces:")
                for i, trace in enumerate(data.get("data", [])[:5], 1):
                    print(f"  {i}. {trace.get('name', 'N/A')} - {trace.get('timestamp', 'N/A')}")
                return True
            else:
                log_warning("No traces found yet (might take a moment to index)")
                return False
        else:
            log_error(f"LangFuse API returned status {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        log_error(f"Cannot query LangFuse traces: {e}")
        return False

def main():
    """Main diagnostic flow"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"BitNet LangFuse Trace Diagnostic")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{Colors.RESET}\n")
    
    # Phase 1: Health checks
    print(f"{Colors.BLUE}[PHASE 1] Health Checks{Colors.RESET}")
    proxy_ok = check_proxy_health()
    langfuse_ok = check_langfuse_health()
    
    if not proxy_ok or not langfuse_ok:
        log_error("Cannot proceed - services not healthy")
        return False
    
    print()
    
    # Phase 2: Trigger traces
    print(f"{Colors.BLUE}[PHASE 2] Triggering Test Traces{Colors.RESET}")
    results = []
    
    results.append(("GET /api/tags", trigger_trace_api_tags()))
    time.sleep(1)
    
    results.append(("GET /v1/models", trigger_trace_openai_models()))
    time.sleep(1)
    
    results.append(("POST /api/generate", trigger_trace_generate()))
    time.sleep(2)
    
    results.append(("POST /v1/chat/completions", trigger_trace_openai_chat()))
    
    print()
    
    # Phase 3: Verify traces in LangFuse
    print(f"{Colors.BLUE}[PHASE 3] Verifying Traces in LangFuse{Colors.RESET}")
    traces_received = check_langfuse_traces()
    
    print()
    
    # Summary
    print(f"{Colors.BLUE}{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}{Colors.RESET}")
    
    successful_triggers = sum(1 for _, result in results if result)
    print(f"Successful API calls: {successful_triggers}/{len(results)}")
    
    for endpoint, result in results:
        status = f"{Colors.GREEN}✓{Colors.RESET}" if result else f"{Colors.RED}✗{Colors.RESET}"
        print(f"  {status} {endpoint}")
    
    print()
    
    if traces_received:
        log_success("Traces are being received and stored in LangFuse!")
        print(f"\n📊 View traces at: {LANGFUSE_UI}")
    else:
        log_warning("Traces may not be reaching LangFuse yet")
        print(f"Check LangFuse dashboard at: {LANGFUSE_UI}")
        print("Allow 5-10 seconds for traces to appear after API calls")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        sys.exit(1)