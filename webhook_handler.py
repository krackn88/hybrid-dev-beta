#!/usr/bin/env python3
"""
GitHub Webhook Handler
Automates GitHub repository updates in real-time using webhooks
"""
import os
import sys
import json
import hmac
import hashlib
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("webhook_handler.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
CONFIG = {
    "repo_owner": os.environ.get("REPO_OWNER", "krackn88"),
    "repo_name": os.environ.get("REPO_NAME", "hybrid-dev-beta"),
    "branch": os.environ.get("BRANCH", "main"),
    "local_path": os.environ.get("LOCAL_PATH", os.path.expanduser("~/hybrid-dev-beta")),
    "webhook_port": int(os.environ.get("WEBHOOK_PORT", 5000)),
    "webhook_secret": os.environ.get("WEBHOOK_SECRET"),
    "github_token": os.environ.get("GITHUB_TOKEN"),
    "auto_commit": os.environ.get("AUTO_COMMIT", "true").lower() in ("true", "1", "yes"),
    "auto_commit_interval": int(os.environ.get("AUTO_COMMIT_INTERVAL", 30)),  # minutes
}

class WebhookHandler(BaseHTTPRequestHandler):
    """Handler for GitHub webhook events"""
    
    def _send_response(self, status_code, message):
        """Send HTTP response with JSON body"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"message": message}).encode('utf-8'))
    
    def do_GET(self):
        """Handle GET request - simple health check"""
        if self.path == '/health':
            self._send_response(200, "Webhook handler is healthy")
        else:
            self._send_response(200, "GitHub webhook handler is running")
    
    def do_POST(self):
        """Handle POST request - GitHub webhook event"""
        if self.path != '/webhook':
            self._send_response(404, "Not found")
            return
        
        # Get content length
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._send_response(400, "Empty payload")
            return
        
        # Read and parse payload
        payload_bytes = self.rfile.read(content_length)
        
        # Verify signature if webhook secret is configured
        if CONFIG["webhook_secret"]:
            signature_header = self.headers.get('X-Hub-Signature-256')
            if not signature_header:
                logger.error("No signature header in request")
                self._send_response(403, "Missing signature header")
                return
            
            if not self._verify_signature(payload_bytes, signature_header):
                logger.error("Invalid signature")
                self._send_response(403, "Invalid signature")
                return
        
        # Parse JSON payload
        try:
            payload = json.loads(payload_bytes.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload")
            self._send_response(400, "Invalid JSON payload")
            return
        
        # Get event type
        event_type = self.headers.get('X-GitHub-Event')
        logger.info(f"Received {event_type} event")
        
        # Handle different event types
        if event_type == 'ping':
            self._send_response(200, "Pong")
        elif event_type == 'push':
            # Check branch
            ref = payload.get('ref')
            if ref != f"refs/heads/{CONFIG['branch']}":
                logger.info(f"Ignoring push to {ref}, we only care about {CONFIG['branch']}")
                self._send_response(200, f"Ignored push to {ref}")
                return
            
            # Process push event
            try:
                self._process_push_event(payload)
                self._send_response(200, "Push event processed successfully")
            except Exception as e:
                logger.error(f"Error processing push event: {str(e)}")
                self._send_response(500, f"Error processing push event: {str(e)}")
        else:
            # Just acknowledge other events
            self._send_response(200, f"Received {event_type} event")
    
    def _verify_signature(self, payload_bytes, signature_header):
        """Verify GitHub webhook signature"""
        if not CONFIG["webhook_secret"]:
            return True
        
        # The signature comes in as "sha256=HASH"
        sha_name, github_signature = signature_header.split('=', 1)
        if sha_name != 'sha256':
            return False
        
        # Calculate expected signature
        mac = hmac.new(
            CONFIG["webhook_secret"].encode('utf-8'),
            msg=payload_bytes,
            digestmod=hashlib.sha256
        )
        expected_signature = mac.hexdigest()
        
        # Compare signatures (using hmac.compare_digest to prevent timing attacks)
        return hmac.compare_digest(github_signature, expected_signature)
    
    def _process_push_event(self, payload):
        """Process push event - update local repository"""
        logger.info(f"Processing push event to {CONFIG['branch']}")
        
        # Ensure local path exists
        local_path = Path(CONFIG["local_path"])
        local_path.mkdir(parents=True, exist_ok=True)
        
        # Check if repo is already cloned
        git_dir = local_path / ".git"
        if not git_dir.exists():
            logger.info(f"Cloning repository to {local_path}")
            clone_url = f"https://{CONFIG['github_token']}@github.com/{CONFIG['repo_owner']}/{CONFIG['repo_name']}.git"
            subprocess.run(
                ["git", "clone", clone_url, str(local_path)],
                check=True,
                capture_output=True
            )
        else:
            logger.info(f"Updating existing repository at {local_path}")
            # Fetch and reset to origin/branch
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=str(local_path),
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "checkout", CONFIG["branch"]],
                cwd=str(local_path),
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "reset", "--hard", f"origin/{CONFIG['branch']}"],
                cwd=str(local_path),
                check=True,
                capture_output=True
            )
        
        logger.info("Repository updated successfully")
        
        # Run post-update actions
        self._run_post_update_actions(local_path)
    
    def _run_post_update_actions(self, repo_path):
        """Run any actions needed after repository update"""
        # Check for package.json in vscode-extension directory
        vscode_dir = repo_path / "vscode-extension"
        if vscode_dir.exists() and (vscode_dir / "package.json").exists():
            logger.info("Building VSCode extension")
            try:
                # Install dependencies and build
                subprocess.run(
                    ["npm", "install"],
                    cwd=str(vscode_dir),
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["npm", "run", "compile"],
                    cwd=str(vscode_dir),
                    check=True,
                    capture_output=True
                )
                logger.info("VSCode extension built successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error building VSCode extension: {e.stderr.decode()}")
        
        # Check for requirements.txt
        if (repo_path / "requirements.txt").exists():
            logger.info("Installing Python dependencies")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                    cwd=str(repo_path),
                    check=True,
                    capture_output=True
                )
                logger.info("Python dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error installing Python dependencies: {e.stderr.decode()}")

def start_webhook_server():
    """Start the webhook server"""
    if not CONFIG["webhook_secret"]:
        logger.warning("WEBHOOK_SECRET not set - webhook signatures won't be verified")
    
    if not CONFIG["github_token"]:
        logger.warning("GITHUB_TOKEN not set - repository operations may fail")
    
    server_address = ('', CONFIG["webhook_port"])
    httpd = HTTPServer(server_address, WebhookHandler)
    
    logger.info(f"Starting webhook server on port {CONFIG['webhook_port']}")
    logger.info("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping webhook server")
        httpd.server_close()

if __name__ == "__main__":
    print(f"GitHub Webhook Handler v1.0.0")
    print(f"Repository: {CONFIG['repo_owner']}/{CONFIG['repo_name']}")
    print(f"Branch: {CONFIG['branch']}")
    print(f"Local path: {CONFIG['local_path']}")
    print(f"Webhook port: {CONFIG['webhook_port']}")
    
    start_webhook_server()