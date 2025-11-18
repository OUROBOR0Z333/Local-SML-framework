#!/bin/bash
# LangFuse Setup and Diagnostics Script

echo "========================================="
echo "LANGFUSE CONNECTION DIAGNOSTICS"
echo "========================================="

echo
echo "Status Check:"
echo "- LangFuse service: $(curl -s http://localhost:3001/api/public/health > /dev/null && echo 'RUNNING' || echo 'NOT RUNNING')"
echo "- BitNet proxy: $(curl -s http://localhost:8001/api/version > /dev/null && echo 'RUNNING' || echo 'NOT RUNNING')"
echo "- BitNet backend: $(curl -s http://localhost:8000/v1/chat/completions -X POST -H 'Content-Type: application/json' -d '{\"model\": \"test\", \"messages\": [{\"role\": \"user\", \"content\": \"test\"}]}' > /dev/null && echo 'RUNNING' || echo 'NOT RUNNING')"

echo
echo "========================================="  
echo "NEXT STEPS"
echo "========================================="
echo
echo "1. OPEN your browser to: http://localhost:3001"
echo
echo "2. Create a new project (sign up with any email/password)"
echo
echo "3. Once your project is created, you will get project-specific API keys"
echo
echo "4. Update your environment with the new keys:"
echo "   export LANGFUSE_PUBLIC_KEY='your_new_public_key'"
echo "   export LANGFUSE_SECRET_KEY='your_new_secret_key'"
echo 
echo "5. Test the proxy endpoints again:"
echo "   curl -X POST http://localhost:8001/v1/chat/completions \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"model\": \"bitnet-b158-2b\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}'"
echo
echo "6. Check the traces in your LangFuse UI at http://localhost:3001"
echo
echo "NOTE: The credentials in the .env file are initial setup credentials."
echo "      After project creation, you must use project-specific API keys."
echo "========================================="
