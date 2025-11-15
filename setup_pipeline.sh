#!/bin/bash

# Script to set up the complete BitNet -> Open WebUI -> Langfuse pipeline

echo "Setting up the complete pipeline: BitNet -> Open WebUI -> Langfuse"
echo "==============================================================="

# Check if required services are running
echo "Checking if required services are running..."

# Check if BitNet Inference Server is running on port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null; then
    echo "✓ BitNet Inference Server is running on port 8000"
else
    echo "✗ BitNet Inference Server is NOT running on port 8000"
    echo "Please start your BitNet server first:"
    echo "cd /home/ouroboroz/Projects/AI/LLMs/BitNet"
    echo "python run_inference_server.py --model models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf --port 8000"
    echo ""
fi

# Check if BitNet Proxy Server is running on port 8001
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null; then
    echo "✓ BitNet Proxy Server is running on port 8001"
else
    echo "✗ BitNet Proxy Server is NOT running on port 8001"
    echo "Please start your BitNet proxy server first:"
    echo "cd /home/ouroboroz/Projects/AI/LLMs/BitNet"
    echo "python -m uvicorn bitnet_ollama_proxy:app --host 0.0.0.0 --port 8001"
    echo ""
fi

# Check if Langfuse is running on port 3001
if lsof -Pi :3001 -sTCP:LISTEN -t >/dev/null; then
    echo "✓ Langfuse is running on port 3001"
else
    echo "✗ Langfuse is NOT running on port 3001"
    echo "Please start Langfuse first:"
    echo "cd /home/ouroboroz/Projects/langfuse"
    echo "docker-compose up -d"
    echo ""
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "✗ Docker is not installed or not in PATH"
    exit 1
else
    echo "✓ Docker is available"
fi

echo ""
echo "Starting Open WebUI with Pipelines (connects to BitNet via proxy)..."
echo "=================================================================="

# Navigate to Open WebUI directory and start the service
cd /home/ouroboroz/Projects/open-webui
echo "Starting Open WebUI with BitNet configuration..."
docker-compose -f docker-compose-bitnet.yml up -d

echo ""
echo "Pipeline setup instructions:"
echo "============================"
echo "1. Open your browser and go to http://localhost:3002"
echo "2. In Open WebUI admin settings, add an Ollama API connection:"
echo "   - URL: http://host.docker.internal:9099"
echo "   - API Key: 0p3n-w3bu! (default)"
echo "3. Go to Pipelines section in admin settings"
echo "4. Install the Langfuse filter pipeline from:"
echo "   https://github.com/open-webui/pipelines/blob/main/examples/filters/langfuse_filter_pipeline.py"
echo "5. Configure your Langfuse credentials in the pipeline settings:"
echo "   - Public Key: your actual public key"
echo "   - Secret Key: your actual secret key" 
echo "   - Host: http://host.docker.internal:3001"
echo ""
echo "Services configuration:"
echo "- BitNet Server: port 8000 (on host)"
echo "- BitNet Proxy: port 8001 (on host)"
echo "- Langfuse: port 3001 (on host)"
echo "- Pipelines: port 9099 (in Docker)"
echo "- Open WebUI: port 3002 (on host)"
echo ""
echo "The complete pipeline flow:"
echo "Open WebUI (3002) -> Pipelines (9099) -> BitNet Proxy (8001) -> BitNet Server (8000)"
echo "All interactions will be traced to Langfuse (3001)"