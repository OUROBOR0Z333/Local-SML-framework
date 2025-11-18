#!/bin/bash
# Test script to verify LangFuse tracing is working with the proxy

echo "Testing BitNet proxy with LangFuse integration..."
echo

# Make a few requests to trigger tracing
echo "Making test requests to proxy..."
curl -s "http://localhost:8001/api/tags" > /dev/null
echo "✓ Request to /api/tags completed"

curl -s "http://localhost:8001/v1/models" > /dev/null  
echo "✓ Request to /v1/models completed"

# Wait a bit for traces to be processed
echo "Waiting 10 seconds for traces to be processed..."
sleep 10

echo
echo "Checking for new traces in LangFuse..."

# Get the current count of traces
current_count=$(curl -u pk-lf-c744a3d3-6166-43d5-a578-7bead547d4ea:sk-lf-03f98e68-54ea-424b-af23-3acb63f06001 -s "http://localhost:3001/api/public/traces" | jq '.meta.totalItems')

echo "Current trace count: $current_count"

# Get the most recent trace
curl -u pk-lf-c744a3d3-6166-43d5-a578-7bead547d4ea:sk-lf-03f98e68-54ea-424b-af23-3acb63f06001 -s "http://localhost:3001/api/public/traces?limit=1" | jq -r '.data[0] | "Most recent trace: \(.name) at \(.timestamp)"'

echo
echo "Test complete."