# BitNet + Open WebUI + Langfuse Integration

This project sets up a complete pipeline with BitNet 1-bit LLM integrated with Open WebUI and monitored with Langfuse for observability.

## Architecture Overview

```
Open WebUI (port 3002) → Pipelines (port 9099) → BitNet Proxy (port 8001) → BitNet Server (port 8000)
                                               ↘ Langfuse (port 3001)
```

## Prerequisites

- Docker and Docker Compose
- Python environment for BitNet server and proxy
- BitNet model files in `/home/ouroboroz/Projects/AI/LLMs/BitNet/models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf`

## Setup Process

### 1. Start BitNet Inference Server

```bash
cd /home/ouroboroz/Projects/AI/LLMs/BitNet
python run_inference_server.py --model models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf --port 8000
```

### 2. Start BitNet Proxy Server

```bash
cd /home/ouroboroz/Projects/AI/LLMs/BitNet
python -m uvicorn bitnet_ollama_proxy:app --host 0.0.0.0 --port 8001
```

### 3. Start Langfuse

```bash
cd /home/ouroboroz/Projects/langfuse
docker-compose up -d
```

Wait for Langfuse to be fully ready (check at http://localhost:3001)

### 4. Start Open WebUI with Pipelines

```bash
cd /home/ouroboroz/Projects/open-webui
docker-compose -f docker-compose-bitnet.yml up -d
```

### 5. Configure Open WebUI

1. Open http://localhost:3002
2. Go to Admin Settings → Models
3. Add a new Ollama API connection:
   - URL: `http://host.docker.internal:9099`
   - API Key: `0p3n-w3bu!`
4. Go to Admin Settings → Pipelines
5. Install the Langfuse filter pipeline from:
   `https://github.com/open-webui/pipelines/blob/main/examples/filters/langfuse_filter_pipeline.py`
6. In the pipeline settings, configure:
   - Secret Key: your Langfuse secret key
   - Public Key: your Langfuse public key
   - Host: `http://host.docker.internal:3001`

### 6. Enable Usage Tracking (Optional)

To capture token usage in Langfuse:
1. Go to Models settings in Open WebUI
2. In the model's Features section, check the "Usage" checkbox

## Configuration Files

- `docker-compose-bitnet.yml` - Docker Compose for Open WebUI with Pipelines
- `pipelines-data/langfuse_filter_pipeline.py` - Langfuse integration pipeline
- `setup_pipeline.sh` - Automation script to check and start services

## Services Ports

- Open WebUI: 3002
- Pipelines: 9099
- BitNet Proxy: 8001
- BitNet Server: 8000
- Langfuse: 3001

## Verification

1. Verify all services are running using `docker ps`
2. Test the connection: Open WebUI → Create a chat → Check Langfuse for traces
3. In Langfuse UI, you should see traces from Open WebUI interactions

## Troubleshooting

- If Docker containers can't reach host services, ensure `host.docker.internal` is properly mapped
- If Langfuse doesn't receive traces, verify pipeline configuration and API keys
- Check container logs with `docker logs <container_name>`

## Shutdown

To stop all services:

```bash
# Stop Open WebUI and Pipelines
cd /home/ouroboroz/Projects/open-webui
docker-compose -f docker-compose-bitnet.yml down

# Stop Langfuse
cd /home/ouroboroz/Projects/langfuse
docker-compose down

# Stop BitNet server and proxy (Ctrl+C in their terminals)
```