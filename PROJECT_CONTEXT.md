# Local LLM Development Stack - Project Context

## Architecture Overview

### Component Deployment Strategy:
- **BitNet model**: Running directly on bare metal (installed directly on the host computer, not in containers)
- **WebUI and Llama (Ollama)**: Running in Docker containers
- **LangFuse**: Will run in Docker container
- **Opik**: Will run in Docker container  
- **Flowise**: Will run in Docker container

### Technical Constraint:
- BitNet-b1.58 uses an architecture with ~1.58-bit weights
- Ollama runs models compatible with llama.cpp (GGUF format) from supported families
- Ollama's "bits" refer to post-training quantization schemes for LLaMA-like architectures only
- **The key blocker is architectural compatibility**: BitNet's architecture is fundamentally different from LLaMA-style models
- llama.cpp (and thus Ollama) does not currently implement the BitNet architecture or have an exporter to GGUF for it
- The limitation is architectural support, not just precision differences

### Architecture Solution:
**FastAPI proxy server** that bridges the architectural gap:
- File: `bitnet_ollama_proxy.py` in `/home/ouroboroz/Projects/AI/LLMs/BitNet/`
- **Purpose**: Translates between Ollama/OpenAI API formats and BitNet's native API
- **Provides**: 
  - Ollama-compatible endpoints (`/api/tags`, `/api/generate`, etc.)
  - OpenAI-compatible endpoints (`/v1/chat/completions`, etc.)
  - Allows Open WebUI to communicate with BitNet through API format translation
- **Architecture**: BitNet (bare metal) → FastAPI Proxy → Ollama/Open WebUI (Docker containers)
- **Port**: Runs on port 8001

### Current State:
- The proxy server exists and is fully implemented with both Ollama and OpenAI API compatibility
- BitNet model is installed on the host system
- Ollama and Open WebUI containers are running but not properly connected to the BitNet proxy
- The proxy needs to be configured to run and connect with the appropriate endpoints

### Implementation Sequence (5-Step Plan):
1. **BitNet model and proxy server** - Started (BitNet installed, proxy server available)
2. **WebUI and Llama** - In progress (Ollama and Open WebUI running but not connected)
3. **LangFuse** - Not yet started
4. **Opik** - Not yet started
5. **Flowise** - Not yet started

### Key Files:
- `/home/ouroboroz/Projects/AI/LLMs/BitNet/bitnet_ollama_proxy.py` - The FastAPI proxy server
- `/home/ouroboroz/Projects/open-webui/` - The WebUI and Ollama Docker setup