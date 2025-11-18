#!/usr/bin/env python3
"""
Smoke-test LangFuse: create a dummy span → verify it exists.
No interaction with your model or proxy required.
"""

import os, time, uuid, sys, requests
from datetime import datetime, timezone

# --- Config (take from your .env) ------------------------------------------
LF_PUBLIC  = os.getenv("LANGFUSE_INIT_PROJECT_PUBLIC_KEY",
                       "pk-lf-9dc915a9-0d54-48fb-ba35-c2d18baac3ba")
LF_SECRET  = os.getenv("LANGFUSE_INIT_PROJECT_SECRET_KEY",
                       "sk-lf-7864c537-79ba-4e28-a87f-3f19f88bfd27")
LF_HOST    = os.getenv("LANGFUSE_HOST", "http://localhost:3001")
# ---------------------------------------------------------------------------

def sdk_test():
    """
    1) Emit a span with the Python SDK
    2) Hit LangFuse public API to see if span was stored
    """
    try:
        from langfuse import Langfuse           # pip install langfuse>=2.0.0
    except ImportError:
        print("❌  'langfuse' package missing →  pip install langfuse")
        sys.exit(1)

    # ---- 1. Emit -----------------------------------------------------------
    lf = Langfuse(public_key=LF_PUBLIC,
                  secret_key=LF_SECRET,
                  host=LF_HOST)

    span_name  = f"smoke-span-{uuid.uuid4().hex[:8]}"
    test_attr  = {"ping": "pong", "ts": datetime.now(timezone.utc).isoformat()}

    span = lf.start_span(name=span_name, input=test_attr)
    span.update(output={"status": "ok"})
    span.end()
    print(f"✅  Sent span '{span_name}' to LangFuse")

    # ---- 2. Verify (simple) -----------------------------------------------
    time.sleep(2)                               # allow indexer to flush
    r = requests.get(f"{LF_HOST}/api/public/traces",
                     auth=(LF_PUBLIC, LF_SECRET),
                     params={"limit": 5},
                     timeout=10)

    if r.status_code != 200:
        print(f"❌  LangFuse query failed: {r.status_code} → {r.text[:120]}")
        sys.exit(1)

    traces = r.json().get("data", [])
    found   = any(span_name in (t.get("name") or "") for t in traces)

    if found:
        print("🎉  Span found in LangFuse → ingestion OK")
        sys.exit(0)
    else:
        print("⚠   Span not visible yet (latency / sampling?)")
        sys.exit(2)


if __name__ == "__main__":
    sdk_test()