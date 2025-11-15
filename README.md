# BitNet 1-bit LLM with Open WebUI

This repository contains the configuration and setup files to run BitNet, a 1-bit LLM, with Open WebUI.

## Architecture

- **BitNet Server**: Runs the 1-bit LLM model
- **BitNet Proxy**: Translates between OpenAI/Ollama API formats and BitNet format
- **Open WebUI**: Web interface to interact with the model

## Prerequisites

- Docker and Docker Compose
- Python environment for BitNet server and proxy
- BitNet model files

## Setup Instructions

### 1. Start BitNet Inference Server

```bash
cd /path/to/BitNet
python run_inference_server.py --model models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf --port 8000
```

### 2. Start BitNet Proxy Server

```bash
cd /path/to/BitNet
python -m uvicorn bitnet_ollama_proxy:app --host 0.0.0.0 --port 8001
```

### 3. Start Open WebUI

```bash
cd /path/to/open-webui
docker-compose -f docker-compose-bitnet.yml up -d
```

### 4. Configure Open WebUI

1. Open http://localhost:3002
2. Complete initial setup
3. Go to Admin Settings → Models
4. Add OpenAI API connection:
   - Base URL: `http://host.docker.internal:8001/v1`
   - API Key: `0p3n-w3bu!`
5. Model name will be `bitnet-b158-2b`

## Files Included

- `docker-compose-bitnet.yml` - Docker configuration for Open WebUI
- `pipelines-data/langfuse_filter_pipeline.py` - Langfuse integration pipeline (optional)
- `setup_pipeline.sh` - Setup automation script
- `README_BITNET_LANGFUSE.md` - Complete documentation
- `.gitignore` - Git ignore file optimized for code-only repository

## Ports

- Open WebUI: 3002
- BitNet Proxy: 8001
- BitNet Server: 8000

## Troubleshooting

- If Docker containers can't reach host services, ensure `host.docker.internal` is properly mapped
- Verify BitNet server and proxy are running before starting Open WebUI
- Check that model files are correctly placed

## Repository Focus

This repository contains only the configuration and source code needed to run the pipeline. Docker volumes, images, and cached data are excluded via .gitignore.