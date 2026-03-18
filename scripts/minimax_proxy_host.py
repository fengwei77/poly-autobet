"""
MiniMax CLI Proxy (Host Side)
Run this on your Windows host to turn 'opencode' CLI into an OpenAI-compatible API.
Usage: python scripts/minimax_proxy_host.py
"""

import os
import json
import subprocess
import shlex
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MiniMaxProxy")

PORT = 8317

class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/v1/chat/completions":
            self.handle_chat()
        else:
            self.send_error(404, "Not Found")

    def handle_chat(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        req_body = json.loads(post_data.decode('utf-8'))
        
        # Extract prompt from last message
        messages = req_body.get("messages", [])
        if not messages:
            self.send_error(400, "No messages")
            return
            
        last_message = messages[-1]["content"]
        logger.info(f"📩 Received request: {last_message[:50]}...")

        # Call opencode run
        try:
            # We use 'opencode run'
            # Note: We need to make sure 'opencode' is in the PATH on Windows
            cmd = f"opencode run {shlex.quote(last_message)}"
            logger.info("🚀 Executing opencode...")
            
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode != 0:
                logger.error(f"❌ opencode failed: {result.stderr}")
                content = f"Error from CLI: {result.stderr}"
            else:
                content = result.stdout.strip()
                logger.success("✅ opencode success")

            # Format as OpenAI response
            response = {
                "id": "chatcmpl-proxy",
                "object": "chat.completion",
                "created": 123456789,
                "model": req_body.get("model", "minimax-proxy"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except Exception as e:
            logger.error(f"💥 Proxy error: {e}")
            self.send_error(500, str(e))

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, ProxyHandler)
    logger.info(f"✨ MiniMax Proxy running on port {PORT}...")
    logger.info("👉 Use base_url='http://host.docker.internal:8317/v1' in your bot.")
    httpd.serve_forever()

if __name__ == "__main__":
    # Monkey patch logger for success message
    logger.success = lambda msg: logger.info(f"SUCCESS: {msg}")
    run_server()
