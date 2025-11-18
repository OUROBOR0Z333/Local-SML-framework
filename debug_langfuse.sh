#!/bin/bash
# LangFuse Debug Script

echo "=== LangFuse Debug Tool ==="
echo "Starting at: $(date)"
echo

# Check if required environment variables are set
echo "1. Checking environment variables..."
if [ -z "$LANGFUSE_PUBLIC_KEY" ] || [ -z "$LANGFUSE_SECRET_KEY" ]; then
    echo "❌ Environment variables not set, loading from .env file..."
    if [ -f "/home/ouroboroz/Projects/AI/LLMs/BitNet/.env" ]; then
        export $(grep -v '^#' /home/ouroboroz/Projects/AI/LLMs/BitNet/.env | xargs)
        echo "✅ Environment variables loaded from .env file"
    else
        echo "❌ .env file not found, please set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY"
        exit 1
    fi
fi

echo "   LANGFUSE_HOST: $LANGFUSE_HOST"
echo "   Public key: ${LANGFUSE_PUBLIC_KEY:0:8}..."
echo "   Secret key: ${LANGFUSE_SECRET_KEY:0:8}..."

echo
echo "2. Checking if LangFuse is running..."
if curl -sf "$LANGFUSE_HOST/api/public/health" > /dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s "$LANGFUSE_HOST/api/public/health")
    echo "✅ LangFuse is running - $HEALTH_RESPONSE"
else
    echo "❌ LangFuse is not responding at $LANGFUSE_HOST"
    echo "   Please make sure LangFuse is running"
    exit 1
fi

echo
echo "3. Checking if proxy is running..."
if curl -sf "http://localhost:8001/v1/models" > /dev/null 2>&1; then
    PROXY_RESPONSE=$(curl -s "http://localhost:8001/v1/models" | head -c 200)
    echo "✅ Proxy is running - Response preview: $PROXY_RESPONSE..."
else
    echo "❌ Proxy is not responding at http://localhost:8001"
    echo "   Please make sure the proxy is running"
    exit 1
fi

echo
echo "4. Running LangFuse tracing test..."
cd /home/ouroboroz/Projects/AI/LLMs/BitNet
python3 debug_langfuse.py

echo
echo "5. Testing a sample request through proxy (this will create traces)..."
curl -s -X POST "http://localhost:8001/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bitnet-b158-2b",
    "messages": [
      {"role": "user", "content": "Debug test - please ignore"}
    ],
    "temperature": 0.7,
    "max_tokens": 10
  }' || echo "Request completed (may have failed if backend not available)"

echo
echo "6. Waiting 30 seconds for traces to be sent to LangFuse..."
sleep 30

echo
echo "DEBUG COMPLETE"
echo "Check your LangFuse UI at: $LANGFUSE_HOST"
echo "Look for traces created in the last few minutes"
echo "Common trace names: debug-test-span, openai-chat-completions, api-models"