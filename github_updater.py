#!/usr/bin/env python3
"""
GitHub Repository Real-Time Updater
No C extensions required, works with minimal dependencies
"""
import os
import sys
import time
import json
import hmac
import hashlib
import logging
import subprocess
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error
import urllib.parse
import http.server
import socketserver
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("github_updater.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration - load from environment variables for security
CONFIG = {
    "repo_owner": os.environ.get("REPO_OWNER", "krackn88"),
    "repo_name": os.environ.get("REPO_NAME", "hybrid-dev-beta"),
    "github_token": os.environ.get("GITHUB_TOKEN"),
    "webhook_secret": os.environ.get("WEBHOOK_SECRET"),
    "branch": os.environ.get("BRANCH", "main"),
    "local_repo_path": os.environ.get("LOCAL_REPO_PATH", str(Path.home() / "hybrid-dev-beta")),
    "extension_dir": "vscode-extension",
    "polling_interval": int(os.environ.get("POLLING_INTERVAL", "60")),
    "webhook_port": int(os.environ.get("WEBHOOK_PORT", "8000")),
}

class GitHubAPI:
    """Simple GitHub API client without external dependencies"""
    
    def __init__(self, token):
        self.token = token
        self.api_base = "https://api.github.com"
        
    def _make_request(self, endpoint, method="GET", data=None):
        """Make a request to the GitHub API"""
        url = f"{self.api_base}{endpoint}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Updater-Script"
        }
        
        req = urllib.request.Request(url, method=method, headers=headers)
        
        if data and method != "GET":
            req.data = json.dumps(data).encode('utf-8')
            
        try:
            with urllib.request.urlopen(req) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            logger.error(f"API request failed: {e.code} - {e.reason}")
            if e.code == 403 and 'rate limit' in str(e.read()):
                logger.warning("Rate limit exceeded, waiting before retrying")
                time.sleep(60)  # Wait a minute before retrying
            error_body = e.read().decode('utf-8')
            logger.error(f"Error details: {error_body}")
            return None
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return None
            
    def get_latest_commit(self, owner, repo, branch):
        """Get the latest commit SHA for a branch"""
        endpoint = f"/repos/{owner}/{repo}/branches/{branch}"
        response = self._make_request(endpoint)
        if response and 'commit' in response:
            return response['commit']['sha']
        return None

class GitHubUpdater:
    """GitHub Repository Updater with no external dependencies"""
    
    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
        self.validate_config()
        self.api = GitHubAPI(self.config["github_token"])
        self.local_repo_path = Path(self.config["local_repo_path"])
        self.extension_dir = self.local_repo_path / self.config["extension_dir"]
        
    def validate_config(self):
        """Validate essential configuration"""
        if not self.config.get("github_token"):
            logger.error("GitHub token is required. Set the GITHUB_TOKEN environment variable.")
            raise ValueError("GitHub token is required")
            
    def clone_or_pull_repo(self):
        """Clone the repository if it doesn't exist, otherwise pull latest changes"""
        try:
            if not (self.local_repo_path / ".git").exists():
                logger.info(f"Cloning repository to {self.local_repo_path}")
                cmd = f"git clone https://{self.config['github_token']}@github.com/{self.config['repo_owner']}/{self.config['repo_name']}.git {self.local_repo_path}"
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
                logger.info("Repository cloned successfully")
            else:
                logger.info("Repository already exists, pulling latest changes")
                cmd = f"cd {self.local_repo_path} && git fetch && git pull origin {self.config['branch']}"
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
                logger.info("Repository updated successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e.stderr.decode() if e.stderr else str(e)}")
            return False
    
    def setup_vscode_extension(self):
        """Set up the VSCode extension"""
        try:
            logger.info("Setting up VSCode extension")
            
            # Create extension directory and src folder
            self.extension_dir.mkdir(parents=True, exist_ok=True)
            (self.extension_dir / "src").mkdir(exist_ok=True)
            
            # Create package.json
            package_json = {
                "name": "vscode-hybrid-extension",
                "displayName": "Hybrid Extension",
                "description": "A VSCode extension for the Hybrid project.",
                "version": "0.0.1",
                "publisher": self.config["repo_owner"],
                "engines": {"vscode": "^1.60.0"},
                "categories": ["Other"],
                "activationEvents": ["onCommand:hybrid.helloWorld"],
                "main": "./out/extension.js",
                "contributes": {
                    "commands": [
                        {"command": "hybrid.helloWorld", "title": "Hello World"},
                        {"command": "hybrid.runTests", "title": "Run Tests"},
                        {"command": "hybrid.buildProject", "title": "Build Project"}
                    ]
                },
                "scripts": {
                    "vscode:prepublish": "npm run compile",
                    "compile": "tsc -p ./",
                    "watch": "tsc -watch -p ./",
                    "package": "vsce package"
                },
                "devDependencies": {
                    "@types/node": "^16.11.7",
                    "@types/vscode": "^1.60.0",
                    "typescript": "^4.5.5",
                    "vsce": "^2.7.0"
                }
            }
            
            with open(self.extension_dir / "package.json", "w") as f:
                json.dump(package_json, f, indent=2)
            
            # Create tsconfig.json
            tsconfig_json = {
                "compilerOptions": {
                    "module": "commonjs",
                    "target": "ES2020",
                    "outDir": "out",
                    "lib": ["ES2020"],
                    "sourceMap": True,
                    "rootDir": "src",
                    "strict": True
                },
                "exclude": ["node_modules", ".vscode-test"]
            }
            
            with open(self.extension_dir / "tsconfig.json", "w") as f:
                json.dump(tsconfig_json, f, indent=2)
            
            # Create extension.ts
            extension_ts = """import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  console.log('Hybrid Extension is now active!');

  // Register hello world command
  let helloCmd = vscode.commands.registerCommand('hybrid.helloWorld', () => {
    vscode.window.showInformationMessage('Hello from Hybrid Extension!');
  });
  context.subscriptions.push(helloCmd);

  // Register run tests command
  let runTestsCmd = vscode.commands.registerCommand('hybrid.runTests', () => {
    vscode.window.showInformationMessage('Running Hybrid Tests...');
  });
  context.subscriptions.push(runTestsCmd);

  // Register build project command
  let buildCmd = vscode.commands.registerCommand('hybrid.buildProject', () => {
    vscode.window.showInformationMessage('Building Hybrid Project...');
  });
  context.subscriptions.push(buildCmd);
}

export function deactivate() {}
"""
            
            with open(self.extension_dir / "src" / "extension.ts", "w") as f:
                f.write(extension_ts)
            
            logger.info("VSCode extension setup completed")
            return True
        except Exception as e:
            logger.error(f"VSCode extension setup failed: {str(e)}")
            return False
    
    def build_extension(self):
        """Build the VSCode extension"""
        try:
            logger.info("Building VSCode extension")
            
            # Install dependencies and build extension
            cmd = f"cd {self.extension_dir} && npm install && npm run compile"
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            
            logger.info("VSCode extension built successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Extension build failed: {e.stderr.decode() if e.stderr else str(e)}")
            return False
    
    def commit_and_push_changes(self):
        """Commit and push changes to the repository"""
        try:
            logger.info("Committing and pushing changes")
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Auto-update: VSCode extension [{timestamp}]"
            
            cmd = f"""
            cd {self.local_repo_path} && 
            git add . && 
            git commit -m "{commit_message}" && 
            git push https://{self.config['github_token']}@github.com/{self.config['repo_owner']}/{self.config['repo_name']}.git {self.config['branch']}
            """
            
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            logger.info("Changes committed and pushed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git push failed: {e.stderr.decode() if e.stderr else str(e)}")
            return False
    
    def full_update_process(self):
        """Run the full update process"""
        logger.info("Starting full update process")
        
        # Clone or pull repository
        if not self.clone_or_pull_repo():
            logger.error("Repository operation failed, aborting update")
            return False
        
        # Setup and build VSCode extension
        if not self.setup_vscode_extension():
            logger.error("VSCode extension setup failed, aborting update")
            return False
        
        if not self.build_extension():
            logger.warning("VSCode extension build failed, but continuing with update")
        
        # Commit and push changes
        if not self.commit_and_push_changes():
            logger.error("Failed to commit and push changes")
            return False
        
        logger.info("Full update process completed successfully")
        return True
    
    def run_polling(self):
        """Poll for repository changes and update when needed"""
        logger.info(f"Starting polling mode with interval: {self.config['polling_interval']} seconds")
        
        last_commit_sha = None
        
        while True:
            try:
                # Get latest commit SHA
                current_commit_sha = self.api.get_latest_commit(
                    self.config['repo_owner'],
                    self.config['repo_name'],
                    self.config['branch']
                )
                
                if current_commit_sha is None:
                    logger.error("Failed to get latest commit. Retrying in next interval.")
                    time.sleep(self.config['polling_interval'])
                    continue
                
                # If this is the first check or the commit has changed
                if last_commit_sha is None or last_commit_sha != current_commit_sha:
                    logger.info(f"New commit detected: {current_commit_sha}")
                    last_commit_sha = current_commit_sha
                    self.full_update_process()
                else:
                    logger.info("No new commits detected")
                
                # Sleep before next check
                time.sleep(self.config['polling_interval'])
                
            except Exception as e:
                logger.error(f"Error during polling: {str(e)}")
                time.sleep(self.config['polling_interval'] * 2)  # Wait longer on error

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    """Simple webhook handler with no external dependencies"""
    
    def _send_response(self, code, message):
        """Send response with JSON body"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(message).encode('utf-8'))
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self._send_response(200, {"status": "healthy", "timestamp": datetime.now().isoformat()})
        else:
            self._send_response(200, {"status": "GitHub webhook receiver is running"})
    
    def do_POST(self):
        """Handle POST requests for GitHub webhooks"""
        if self.path != '/webhook':
            self._send_response(404, {"error": "Not found"})
            return
        
        # Get request headers
        content_length = int(self.headers.get('Content-Length', 0))
        signature_header = self.headers.get('X-Hub-Signature-256', '')
        event_type = self.headers.get('X-GitHub-Event', '')
        
        # Read and parse payload
        payload_body = self.rfile.read(content_length)
        
        # Verify signature
        if not self._verify_signature(payload_body, signature_header):
            logger.error("Webhook signature verification failed")
            self._send_response(403, {"error": "Invalid signature"})
            return
        
        # Parse JSON payload
        try:
            payload = json.loads(payload_body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload")
            self._send_response(400, {"error": "Invalid JSON payload"})
            return
        
        # Handle push event
        if event_type == 'push' and payload.get('ref') == f"refs/heads/{CONFIG['branch']}":
            logger.info(f"Push event detected on {CONFIG['branch']} branch. Triggering repo update.")
            
            # Start update process in a separate thread
            updater = GitHubUpdater(CONFIG)
            threading.Thread(target=updater.full_update_process).start()
            
            self._send_response(202, {"message": "Update process started"})
        else:
            # For other events, just acknowledge receipt
            logger.info(f"Received {event_type} event, but no action needed")
            self._send_response(200, {"message": "Event received"})
    
    def _verify_signature(self, payload_body, signature_header):
        """Verify that the webhook payload was sent from GitHub"""
        if not CONFIG.get('webhook_secret') or not signature_header:
            return False
        
        # The signature comes in as "sha256=<hash>"
        sha_name, github_signature = signature_header.split('=', 1)
        if sha_name != 'sha256':
            return False
        
        # Calculate expected signature
        mac = hmac.new(
            CONFIG['webhook_secret'].encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = mac.hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(github_signature, expected_signature)
    
    def log_message(self, format, *args):
        """Override to send logs to our logger instead of stderr"""
        logger.info("%s - %s" % (self.address_string(), format % args))

def start_webhook_server(port=8000):
    """Start the webhook server"""
    handler = WebhookHandler
    httpd = socketserver.TCPServer(("", port), handler)
    logger.info(f"Starting webhook server on port {port}")
    httpd.serve_forever()

def main():
    """Main function to run the GitHub updater"""
    logger.info("Starting GitHub Repository Updater")
    
    try:
        # Validate token
        if not CONFIG.get("github_token"):
            logger.error("GitHub token not found. Please set the GITHUB_TOKEN environment variable.")
            sys.exit(1)
        
        # Create updater instance
        updater = GitHubUpdater(CONFIG)
        
        # Determine mode: webhook or polling
        if CONFIG.get("webhook_secret"):
            logger.info("Running in webhook mode")
            webhook_thread = threading.Thread(
                target=start_webhook_server,
                args=(CONFIG['webhook_port'],)
            )
            webhook_thread.daemon = True
            webhook_thread.start()
            
            # Run initial update
            updater.full_update_process()
            
            # Keep main thread alive
            while True:
                time.sleep(3600)  # Sleep for an hour
        else:
            logger.info("Running in polling mode")
            updater.run_polling()
            
    except KeyboardInterrupt:
        logger.info("Updater stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()