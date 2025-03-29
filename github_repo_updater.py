#!/usr/bin/env python3
"""
GitHub Repository Updater
Real-time automation for the hybrid-dev-beta repository
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
import requests
from flask import Flask, request, jsonify
from threading import Thread
from github import Github, GithubException

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
    "extension_name": "vscode-hybrid-extension",
    "polling_interval": int(os.environ.get("POLLING_INTERVAL", "60")),
    "webhook_port": int(os.environ.get("WEBHOOK_PORT", "5000")),
    "webhook_endpoint": os.environ.get("WEBHOOK_ENDPOINT", "/github-webhook"),
    "webhook_host": os.environ.get("WEBHOOK_HOST", "0.0.0.0"),
}

# Create Flask app for webhook handler
app = Flask(__name__)

class GitHubUpdater:
    """GitHub Repository Updater Class"""
    
    def __init__(self, config=None):
        """Initialize with configuration"""
        self.config = config or CONFIG
        self.validate_config()
        self.github = Github(self.config["github_token"])
        self.repo = self.github.get_repo(f"{self.config['repo_owner']}/{self.config['repo_name']}")
        self.local_repo_path = Path(self.config["local_repo_path"])
        self.extension_dir = self.local_repo_path / self.config["extension_dir"]
        
        # Create directories if they don't exist
        self.local_repo_path.mkdir(parents=True, exist_ok=True)
        
    def validate_config(self):
        """Validate essential configuration"""
        if not self.config.get("github_token"):
            logger.error("GitHub token is required. Set the GITHUB_TOKEN environment variable.")
            raise ValueError("GitHub token is required")
            
        # For webhook mode, webhook secret is required
        if self.is_webhook_mode() and not self.config.get("webhook_secret"):
            logger.error("Webhook secret is required for webhook mode. Set the WEBHOOK_SECRET environment variable.")
            raise ValueError("Webhook secret is required for webhook mode")
    
    def is_webhook_mode(self):
        """Check if running in webhook mode"""
        return bool(self.config.get("webhook_secret"))
    
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
                "name": self.config["extension_name"],
                "displayName": "Hybrid Extension",
                "description": "A VSCode extension for the Hybrid project.",
                "version": "0.0.1",
                "publisher": self.config["repo_owner"],
                "engines": {"vscode": "^1.60.0"},
                "categories": ["Other"],
                "activationEvents": ["onCommand:hybrid.helloWorld", "onView:hybrid.sidebar"],
                "main": "./out/extension.js",
                "contributes": {
                    "commands": [
                        {"command": "hybrid.helloWorld", "title": "Hello World"},
                        {"command": "hybrid.runTests", "title": "Run Tests"},
                        {"command": "hybrid.buildProject", "title": "Build Project"},
                        {"command": "hybrid.showStatus", "title": "Show Hybrid Status"}
                    ],
                    "viewsContainers": {
                        "activitybar": [
                            {
                                "id": "hybrid-sidebar",
                                "title": "Hybrid Tools",
                                "icon": "resources/icon.png"
                            }
                        ]
                    },
                    "views": {
                        "hybrid-sidebar": [
                            {
                                "id": "hybrid.sidebar",
                                "name": "Hybrid Controls"
                            }
                        ]
                    }
                },
                "scripts": {
                    "vscode:prepublish": "npm run compile",
                    "compile": "tsc -p ./",
                    "watch": "tsc -watch -p ./",
                    "pretest": "npm run compile",
                    "test": "node ./out/test/runTest.js",
                    "package": "vsce package"
                },
                "devDependencies": {
                    "@types/node": "^16.11.7",
                    "@types/vscode": "^1.60.0",
                    "@vscode/test-electron": "^2.1.2", 
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

  // Add Status Bar Information
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = 'hybrid.showStatus';
  statusBarItem.text = 'Hybrid Status';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // Register show status command
  let statusCmd = vscode.commands.registerCommand('hybrid.showStatus', () => {
    vscode.window.showInformationMessage('Hybrid Extension is active and running!');
  });
  context.subscriptions.push(statusCmd);

  // Register sidebar provider for WebView UI
  const sidebarProvider = new SidebarProvider(context.extensionUri);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebarProvider)
  );
}

export function deactivate() {}

class SidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'hybrid.sidebar';
  private _view?: vscode.WebviewView;

  constructor(private readonly _extensionUri: vscode.Uri) {}

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this._extensionUri]
    };
    webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);
  }

  private _getHtmlForWebview(webview: vscode.Webview): string {
    return `<!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body { padding: 10px; }
          button {
            padding: 8px;
            margin: 5px 0;
            width: 100%;
          }
        </style>
        <title>Hybrid Sidebar</title>
      </head>
      <body>
        <h2>Hybrid Controls</h2>
        <button id="runTests">Run Tests</button>
        <button id="buildProject">Build Project</button>
        <button id="showStatus">Show Status</button>
        
        <script>
          const vscode = acquireVsCodeApi();
          
          document.getElementById('runTests').addEventListener('click', () => {
            vscode.postMessage({ command: 'runTests' });
          });
          
          document.getElementById('buildProject').addEventListener('click', () => {
            vscode.postMessage({ command: 'buildProject' });
          });
          
          document.getElementById('showStatus').addEventListener('click', () => {
            vscode.postMessage({ command: 'showStatus' });
          });
        </script>
      </body>
      </html>`;
  }
}
"""
            
            with open(self.extension_dir / "src" / "extension.ts", "w") as f:
                f.write(extension_ts)
            
            # Create .vscodeignore
            vscodeignore = """
.vscode/**
.vscode-test/**
node_modules/**
src/**
.gitignore
.yarnrc
webpack.config.js
vsc-extension-quickstart.md
**/*.map
**/*.ts
"""
            
            with open(self.extension_dir / ".vscodeignore", "w") as f:
                f.write(vscodeignore)
            
            # Create resources directory for icons
            (self.extension_dir / "resources").mkdir(exist_ok=True)
            
            logger.info("VSCode extension setup completed")
            return True
        except Exception as e:
            logger.error(f"VSCode extension setup failed: {str(e)}")
            return False
    
    def build_extension(self):
        """Build the VSCode extension"""
        try:
            logger.info("Building VSCode extension")
            
            # Set up a simple placeholder icon if it doesn't exist
            icon_path = self.extension_dir / "resources" / "icon.png"
            if not icon_path.exists():
                # This is a very simple 1x1 pixel PNG (base64 encoded)
                with open(icon_path, "wb") as f:
                    f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\rZ\\\xef\x00\x00\x00\x00IEND\xaeB`\x82')
            
            # Install dependencies and build extension
            cmd = f"cd {self.extension_dir} && npm install && npm run compile"
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            
            # Package extension
            cmd = f"cd {self.extension_dir} && npm run package"
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
                branch = self.repo.get_branch(self.config['branch'])
                current_commit_sha = branch.commit.sha
                
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

def verify_webhook_signature(payload_body, signature_header, secret):
    """Verify that the webhook payload was sent from GitHub"""
    if not signature_header:
        return False
    
    expected_signature = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature_header, expected_signature)

@app.route('/', methods=['GET'])
def index():
    """Simple index route to verify server is running"""
    return jsonify({"status": "GitHub webhook receiver is running"})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/github-webhook', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook events"""
    signature_header = request.headers.get('X-Hub-Signature-256')
    
    # Verify webhook signature
    if not verify_webhook_signature(request.data, signature_header, CONFIG['webhook_secret']):
        logger.error("Webhook signature verification failed")
        return jsonify({"error": "Invalid signature"}), 403
    
    # Parse the event payload
    event = request.headers.get('X-GitHub-Event')
    payload = request.json
    
    # Check if this is a push event to the main branch
    if event == 'push' and payload.get('ref') == f"refs/heads/{CONFIG['branch']}":
        logger.info(f"Push event detected on {CONFIG['branch']} branch. Triggering repo update.")
        
        # Start update process in a separate thread
        updater = GitHubUpdater(CONFIG)
        Thread(target=updater.full_update_process).start()
        
        return jsonify({"message": "Update process started"}), 202
    
    # For other events, just acknowledge receipt
    logger.info(f"Received {event} event, but no action needed")
    return jsonify({"message": "Event received"}), 200

def run_webhook_server():
    """Run the webhook server"""
    logger.info(f"Starting webhook server on {CONFIG['webhook_host']}:{CONFIG['webhook_port']}")
    app.run(
        host=CONFIG['webhook_host'],
        port=CONFIG['webhook_port']
    )

def main():
    """Main function to run the GitHub updater"""
    logger.info("Starting GitHub Repository Updater")
    
    try:
        # Validate token
        if not CONFIG.get("github_token"):
            logger.error("GitHub token not found. Please set the GITHUB_TOKEN environment variable.")
            return
        
        # Determine mode: webhook or polling
        if CONFIG.get("webhook_secret"):
            logger.info("Running in webhook mode")
            run_webhook_server()
        else:
            logger.info("Running in polling mode")
            updater = GitHubUpdater(CONFIG)
            updater.run_polling()
            
    except KeyboardInterrupt:
        logger.info("Updater stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()