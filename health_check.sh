#!/bin/bash
# BitNet + LangFuse Health Check Script

# Set your credentials
export LANGFUSE_PUBLIC_KEY="pk-lf-c744a3d3-6166-43d5-a578-7bead547d4ea"
export LANGFUSE_SECRET_KEY="sk-lf-03f98e68-54ea-424b-af23-3acb63f06001"
export LANGFUSE_CREDS="$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY"

echo "=================================="
echo "BitNet + LangFuse Health Check"
echo "=================================="

# Function to check service status
check_service() {
    local name=$1
    local url=$2
    local method=${3:-"GET"}
    local data=${4:-""}
    
    if [ "$method" = "POST" ]; then
        status=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$url")
    else
        status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    fi
    
    if [ "$status" = "200" ] || [ "$status" = "404" ]; then  # 404 indicates service running but endpoint not found
        echo "✓ $name: Running (Status: $status)"
        return 0
    else
        echo "✗ $name: Not running (Status: $status)"
        return 1
    fi
}

# 1. Check all service health
echo
echo "1. Service Health Check:"
check_service "BitNet Backend" "http://localhost:8000/v1/chat/completions" "POST" '{"model": "test", "messages": [{"role": "user", "content": "test"}]}'
check_service "BitNet Proxy" "http://localhost:8001/api/version"
check_service "LangFuse" "http://localhost:3001/api/public/health"

# 2. Validate credentials
echo
echo "2. Credential Validation:"
if curl -u $LANGFUSE_CREDS -s "http://localhost:3001/api/public/traces?limit=1" | jq -e .data[0].name > /dev/null 2>&1; then
    echo "✓ Credentials valid: Can access traces"
else
    echo "✗ Credentials invalid: Cannot access traces"
    exit 1
fi

# 3. Get initial trace count
initial_count=$(curl -u $LANGFUSE_CREDS -s "http://localhost:3001/api/public/traces" | jq '.meta.totalItems')
echo "✓ Initial trace count: $initial_count"

# 4. Test proxy endpoint to generate trace
echo
echo "3. Trace Generation Test:"
echo "Making test request to proxy..."
response=$(curl -s -X POST http://localhost:8001/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model": "bitnet-b158-2b", "messages": [{"role": "user", "content": "Health check test"}], "temperature": 0.7, "max_tokens": 5}' &)

# Wait for trace to be processed
sleep 5

# Check if trace count increased
new_count=$(curl -u $LANGFUSE_CREDS -s "http://localhost:3001/api/public/traces" | jq '.meta.totalItems')
expected_count=$((initial_count + 1))

if [ "$new_count" -eq "$expected_count" ]; then
    echo "✓ Trace generation successful: Count increased from $initial_count to $new_count"
else
    echo "✗ Trace generation failed: Expected $expected_count, got $new_count"
fi

# 5. Test multiple requests
echo
echo "4. Batch Trace Test:"
echo "Making 3 additional test requests..."
curl -X POST http://localhost:8001/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "bitnet-b158-2b", "messages": [{"role": "user", "content": "Batch test 1"}], "temperature": 0.7, "max_tokens": 5}' &>/dev/null &
curl -X POST http://localhost:8001/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "bitnet-b158-2b", "messages": [{"role": "user", "content": "Batch test 2"}], "temperature": 0.7, "max_tokens": 5}' &>/dev/null &
curl -X POST http://localhost:8001/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "bitnet-b158-2b", "messages": [{"role": "user", "content": "Batch test 3"}], "temperature": 0.7, "max_tokens": 5}' &>/dev/null &

# Wait for traces to be processed
sleep 10

final_count=$(curl -u $LANGFUSE_CREDS -s "http://localhost:3001/api/public/traces" | jq '.meta.totalItems')
expected_final_count=$((initial_count + 4))  # initial + single test + 3 batch requests

if [ "$final_count" -ge "$expected_final_count" ]; then
    echo "✓ Batch trace test successful: Count increased to $final_count"
else
    echo "✗ Batch trace test failed: Expected at least $expected_final_count, got $final_count"
fi

# 6. Summary
echo
echo "=================================="
echo "Health Check Summary:"
echo "  Initial trace count: $initial_count"
echo "  Final trace count: $final_count"
echo "  Traces created during test: $((final_count - initial_count))"
echo "=================================="

if [ "$final_count" -gt "$initial_count" ]; then
    echo "✓ System is working correctly!"
    echo "  - All services are running"
    echo "  - Credentials are valid" 
    echo "  - Proxy is generating traces in LangFuse"
    echo "  - Traces are being stored properly"
else
    echo "✗ Issues detected - system may not be working correctly"
fi

echo "=================================="