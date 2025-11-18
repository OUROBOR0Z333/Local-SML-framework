# BitNet + Open WebUI + LangFuse Integration

This repository contains the configuration files needed to set up a complete local LLM development stack with BitNet, Open WebUI, and LangFuse integration.

## Architecture

The system consists of three main components:

### 1. BitNet Configuration
- `bitnet-config/bitnet_ollama_proxy.py`: Proxy that translates between API formats and integrates LangFuse tracing
- `bitnet-config/requirements.txt`: Dependencies including python-dotenv for proper environment loading

### 2. Open WebUI Configuration  
- `openwebui-config/docker-compose-bitnet.yml`: Docker configuration that routes requests through tracing pipeline
- `openwebui-config/langfuse_filter_pipeline.py`: Pipeline that intercepts and traces all requests

### 3. LangFuse Configuration
- `langfuse-config/docker-compose.yml`: Configuration with port updates for integration

## Setup Instructions

1. Install dependencies:
   ```bash
   cd bitnet-config
   pip install -r requirements.txt
   ```

2. Start services in order:
   - Start LangFuse first
   - Start BitNet server
   - Start BitNet proxy
   - Start Open WebUI

3. The LangFuse integration will automatically trace all conversations