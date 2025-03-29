#!/bin/bash
# GitHub Repository Automation Setup Script
# Version: 1.0.0
# Builds on existing ngrok webhook setup

# ===== CONFIGURATION =====
REPO_OWNER="krackn88"
REPO_NAME="hybrid-dev-beta"
BRANCH="main"
LOCAL_PATH="$HOME/$REPO_NAME"
VENV_NAME="repo-automation"
PYTHON_VERSION="3.10"
WEBHOOK_SECRET="bb18eb81289f7b5cc8e195e7f415b2647b7dd22b"  # Already set up
WEBHOOK_URL="https://1257-2600-2b00-a262-ff00-f43f-fd5e-77af-f19.ngrok-free.app/webhook"  # Already set up
LOG_FILE="repo_automation.log"

# ===== COLORS =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===== LOGGING =====
log() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${timestamp} - $1" | tee -a "$LOG_FILE"
}

log_success() { log "${GREEN}SUCCESS: $1${NC}"; }
log_info() { log "${BLUE}INFO: $1${NC}"; }
log_warning() { log "${YELLOW}WARNING: $1${NC}"; }
log_error() { log "${RED}ERROR: $1${NC}"; }

# ===== ERROR HANDLING =====
handle_error() {
    local exit_code=$?
    local line_number=$1
    
    if [ $exit_code -ne 0 ]; then
        log_error "Failed at line $line_number with exit code $exit_code"
        
        # Ask if user wants to continue
        read -p "Continue despite error? (y/n): " continue_choice
        if [[ $continue_choice != "y" && $continue_choice != "Y" ]]; then
            exit $exit_code
        fi
    fi
}

trap 'handle_error $LINENO' ERR

# ===== PYTHON ENVIRONMENT SETUP =====
setup_python_environment() {
    log_info "Setting up Python virtual environment..."
    
    # Ensure Python is installed
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$HOME/$VENV_NAME" ]; then
        python3 -m venv "$HOME/$VENV_NAME"
        log_success "Created virtual environment at $HOME/$VENV_NAME"
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$HOME/$VENV_NAME/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install required packages
    log_info "Installing required Python packages..."
    pip install PyGitHub requests Flask python-dotenv schedule watchdog colorama
    
    log_success "Python environment setup completed"
}

# ===== REPOSITORY SETUP =====
setup_repository() {
    log_info "Setting up repository..."
    
    # Check if GitHub token is set
    if [ -z "$GITHUB_TOKEN" ]; then
        log_error "GITHUB_TOKEN environment variable is not set"
        log_info "Set it with: export GITHUB_TOKEN=your_token_here"
        exit 1
    fi
    
    # Clone repository if it doesn't exist
    if [ ! -d "$LOCAL_PATH" ]; then
        log_info "Cloning repository..."
        git clone "https://$GITHUB_TOKEN@github.com/$REPO_OWNER/$REPO_NAME.git" "$LOCAL_PATH"
    else
        log_info "Repository already exists, updating..."
        cd "$LOCAL_PATH"
        git fetch origin
        git reset --hard "origin/$BRANCH"
    fi
    
    log_success "Repository setup completed"
}

# ===== CREATE PYTHON AUTOMATION SCRIPTS =====
create_automation_scripts() {
    log_info "Creating Python automation scripts..."
    
    # Create directory for automation scripts
    mkdir -p "$LOCAL_PATH/automation"
    
    # Create core automation module
    cat > "$LOCAL_PATH/automation/repo_sync.py" << 'EOL'
#!/usr/bin/env python3
"""
GitHub Repository Synchronization Tool
Maintains synchronization between local and remote repositories
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
import threading
import schedule
import github
from flask import Flask, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("repo_sync.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
CONFIG = {
    "repo_owner": os.environ.get("REPO_OWNER", "krackn88"),
    "repo_name": os.environ.get("REPO_NAME", "hybrid-dev-beta"),
    "github_token": os.environ.get("GITHUB_TOKEN"),
    "webhook_secret": os.environ.get("WEBHOOK_SECRET"),
    "local_path": os.environ.get("LOCAL_PATH", str(Path.home() / "hybrid-dev-beta")),
    "branch": os.environ.get("BRANCH", "main"),
    "auto_commit_interval": int(os.environ.get("AUTO_COMMIT_INTERVAL", "30")),  # minutes
    "webhook_port": int(os.environ.get("WEBHOOK_PORT", "5000")),
    "poll_interval": int(os.environ.get("POLL_INTERVAL", "300")),  # seconds
}

# Initialize Flask app for webhook
app = Flask(__name__)

class RepoSync:
    """Main repository synchronization class"""
    
    def __init__(self, config=None):
        """Initialize with configuration"""
        self.config = config or CONFIG
        self.validate_config()
        self.github = github.Github(self.config["github_token"])
        self.repo = self.github.get_repo(f"{self.config['repo_owner']}/{self.config['repo_name']}")
        self.local_path = Path(self.config["local_path"])
        self.last_commit_sha = None
        self.is_syncing = False
        self.sync_lock = threading.Lock()
        
    def validate_config(self):
        """Validate essential configuration"""
        if not self.config.get("github_token"):
            logger.error("GitHub token is required. Set the GITHUB_TOKEN environment variable.")
            raise ValueError("GitHub token is required")
    
    def pull_repo(self):
        """Pull latest changes from remote repository"""
        logger.info(f"{Fore.BLUE}Pulling latest changes from remote repository{Style.RESET_ALL}")
        
        with self.sync_lock:
            self.is_syncing = True
            try:
                cmd = f"cd {self.local_path} && git fetch origin && git reset --hard origin/{self.config['branch']}"
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
                logger.info(f"{Fore.GREEN}Repository pulled successfully{Style.RESET_ALL}")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"{Fore.RED}Failed to pull repository: {e.stderr.decode()}{Style.RESET_ALL}")
                return False
            finally:
                self.is_syncing = False
    
    def commit_and_push(self, commit_message=None):
        """Commit local changes and push to remote repository"""
        if not commit_message:
            commit_message = f"Auto-update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        logger.info(f"{Fore.BLUE}Checking for local changes{Style.RESET_ALL}")
        
        with self.sync_lock:
            self.is_syncing = True
            try:
                # Check if there are changes to commit
                cmd = f"cd {self.local_path} && git status --porcelain"
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
                
                if not result.stdout.strip():
                    logger.info(f"{Fore.YELLOW}No changes to commit{Style.RESET_ALL}")
                    return True
                
                logger.info(f"{Fore.BLUE}Committing and pushing changes{Style.RESET_ALL}")
                
                # Add all changes
                cmd = f"cd {self.local_path} && git add ."
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
                
                # Commit changes
                cmd = f"cd {self.local_path} && git commit -m \"{commit_message}\""
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
                
                # Push to remote
                cmd = f"cd {self.local_path} && git push origin {self.config['branch']}"
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
                
                logger.info(f"{Fore.GREEN}Changes committed and pushed successfully{Style.RESET_ALL}")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"{Fore.RED}Failed to commit and push: {e.stderr.decode()}{Style.RESET_ALL}")
                return False
            finally:
                self.is_syncing = False
    
    def check_remote_updates(self):
        """Check if there are updates in the remote repository"""
        try:
            # Get latest commit from remote
            branch = self.repo.get_branch(self.config["branch"])
            current_commit_sha = branch.commit.sha
            
            # If this is the first check or the commit has changed
            if self.last_commit_sha is None or self.last_commit_sha != current_commit_sha:
                logger.info(f"{Fore.BLUE}Remote repository has new commits{Style.RESET_ALL}")
                self.last_commit_sha = current_commit_sha
                return True
            
            logger.info(f"{Fore.BLUE}No new commits in remote repository{Style.RESET_ALL}")
            return False
        except Exception as e:
            logger.error(f"{Fore.RED}Failed to check remote updates: {str(e)}{Style.RESET_ALL}")
            return False
    
    def get_latest_changes(self):
        """Pull if remote has updates"""
        if self.check_remote_updates():
            return self.pull_repo()
        return True
    
    def sync_repo(self):
        """Synchronize repository (pull then push)"""
        logger.info(f"{Fore.BLUE}Starting repository synchronization{Style.RESET_ALL}")
        
        if self.is_syncing:
            logger.info(f"{Fore.YELLOW}Synchronization already in progress, skipping{Style.RESET_ALL}")
            return
        
        with self.sync_lock:
            # First pull latest changes
            self.pull_repo()
            
            # Then commit and push any local changes
            self.commit_and_push()
            
        logger.info(f"{Fore.GREEN}Repository synchronization completed{Style.RESET_ALL}")
    
    def start_auto_sync(self):
        """Start automatic synchronization at regular intervals"""
        interval_minutes = self.config["auto_commit_interval"]
        logger.info(f"{Fore.BLUE}Starting auto-sync every {interval_minutes} minutes{Style.RESET_ALL}")
        
        # Schedule regular syncs
        schedule.every(interval_minutes).minutes.do(self.sync_repo)
        
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def start_file_watcher(self):
        """Start watching for file changes"""
        logger.info(f"{Fore.BLUE}Starting file watcher for {self.local_path}{Style.RESET_ALL}")
        
        event_handler = RepoFileHandler(self)
        observer = Observer()
        observer.schedule(event_handler, str(self.local_path), recursive=True)
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


class RepoFileHandler(FileSystemEventHandler):
    """Handler for file system events"""
    
    def __init__(self, repo_sync):
        self.repo_sync = repo_sync
        self.last_event_time = datetime.now()
        self.cooldown_period = 60  # seconds
        self.pending_sync = False
        self.sync_timer = None
    
    def on_any_event(self, event):
        """Handle any file system event"""
        # Ignore .git directory
        if ".git" in event.src_path:
            return
        
        # Ignore sync events
        if self.repo_sync.is_syncing:
            return
        
        # Check if we're in cooldown
        current_time = datetime.now()
        if (current_time - self.last_event_time).total_seconds() < self.cooldown_period:
            # We're in cooldown, cancel existing timer and schedule a new one
            if self.sync_timer:
                self.sync_timer.cancel()
            
            self.pending_sync = True
            self.sync_timer = threading.Timer(self.cooldown_period, self.sync_changes)
            self.sync_timer.start()
        else:
            # We're not in cooldown, sync immediately
            self.last_event_time = current_time
            self.sync_changes()
    
    def sync_changes(self):
        """Sync changes after cooldown"""
        if self.pending_sync:
            logger.info(f"{Fore.BLUE}File changes detected, syncing repository{Style.RESET_ALL}")
            self.repo_sync.sync_repo()
            self.pending_sync = False


def verify_webhook_signature(payload_body, signature_header, secret):
    """Verify GitHub webhook signature"""
    if not signature_header:
        return False
    
    # Get signature hash
    sha_name, signature = signature_header.split('=', 1)
    if sha_name != 'sha256':
        return False
    
    # Calculate expected signature
    mac = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(signature, expected_signature)


@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({"status": "GitHub webhook handler is running"})


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle GitHub webhook events"""
    # Get webhook signature
    signature_header = request.headers.get('X-Hub-Signature-256')
    
    # Verify signature
    if not verify_webhook_signature(request.data, signature_header, CONFIG["webhook_secret"]):
        logger.warning(f"{Fore.RED}Invalid webhook signature{Style.RESET_ALL}")
        return jsonify({"error": "Invalid signature"}), 403
    
    # Get event type
    event_type = request.headers.get('X-GitHub-Event')
    
    # Handle push event
    if event_type == 'push':
        payload = request.json
        ref = payload.get('ref', '')
        
        # Check if push is to our branch
        if ref == f"refs/heads/{CONFIG['branch']}":
            logger.info(f"{Fore.GREEN}Received push event for {CONFIG['branch']} branch{Style.RESET_ALL}")
            
            # Start sync in a new thread
            repo_sync = RepoSync(CONFIG)
            threading.Thread(target=repo_sync.pull_repo).start()
            
            return jsonify({"status": "success", "message": "Pull started"}), 200
    
    # For other events, just acknowledge
    return jsonify({"status": "success", "message": "Event received"}), 200


def start_webhook_server():
    """Start the webhook server"""
    logger.info(f"{Fore.BLUE}Starting webhook server on port {CONFIG['webhook_port']}{Style.RESET_ALL}")
    app.run(host='0.0.0.0', port=CONFIG['webhook_port'])


def start_polling_mode():
    """Start polling mode for repository updates"""
    logger.info(f"{Fore.BLUE}Starting polling mode with interval {CONFIG['poll_interval']} seconds{Style.RESET_ALL}")
    
    repo_sync = RepoSync(CONFIG)
    
    while True:
        try:
            repo_sync.get_latest_changes()
            time.sleep(CONFIG["poll_interval"])
        except Exception as e:
            logger.error(f"{Fore.RED}Error in polling loop: {str(e)}{Style.RESET_ALL}")
            time.sleep(CONFIG["poll_interval"] * 2)  # Wait longer on error


def main():
    """Main entry point"""
    logger.info(f"{Fore.GREEN}Starting GitHub Repository Sync Tool{Style.RESET_ALL}")
    
    # Check for GitHub token
    if not CONFIG.get("github_token"):
        logger.error(f"{Fore.RED}GitHub token not found. Set GITHUB_TOKEN environment variable.{Style.RESET_ALL}")
        sys.exit(1)
    
    # Create repository sync instance
    repo_sync = RepoSync(CONFIG)
    
    # Initial repo pull
    repo_sync.pull_repo()
    
    # Start file watcher thread
    file_watcher_thread = threading.Thread(target=repo_sync.start_file_watcher)
    file_watcher_thread.daemon = True
    file_watcher_thread.start()
    
    # Start auto sync thread
    auto_sync_thread = threading.Thread(target=repo_sync.start_auto_sync)
    auto_sync_thread.daemon = True
    auto_sync_thread.start()
    
    # Start webhook server if webhook secret is set
    if CONFIG.get("webhook_secret"):
        start_webhook_server()
    else:
        # Fall back to polling mode
        start_polling_mode()


if __name__ == "__main__":
    main()
EOL

    # Create webhook handler
    cat > "$LOCAL_PATH/automation/webhook_handler.py" << 'EOL'
#!/usr/bin/env python3
"""
GitHub Webhook Handler
Processes GitHub webhook events and triggers repository updates
"""
import os
import sys
import logging
from repo_sync import RepoSync, app, CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("webhook_handler.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    logger.info("Starting GitHub Webhook Handler")
    
    # Check for required environment variables
    if not CONFIG.get("github_token"):
        logger.error("GitHub token not found. Set GITHUB_TOKEN environment variable.")
        sys.exit(1)
    
    if not CONFIG.get("webhook_secret"):
        logger.error("Webhook secret not found. Set WEBHOOK_SECRET environment variable.")
        sys.exit(1)
    
    # Start the webhook server
    app.run(host='0.0.0.0', port=CONFIG.get("webhook_port", 5000))

if __name__ == "__main__":
    main()
EOL

    # Create utility script
    cat > "$LOCAL_PATH/automation/repo_utils.py" << 'EOL'
#!/usr/bin/env python3
"""
Repository Utility Functions
Provides helper functions for repository automation
"""
import os
import sys
import json
import logging
import subprocess
import argparse
from pathlib import Path
from repo_sync import RepoSync, CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("repo_utils.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def pull_repository():
    """Pull latest changes from remote repository"""
    repo_sync = RepoSync(CONFIG)
    return repo_sync.pull_repo()

def push_changes(commit_message=None):
    """Commit and push changes to remote repository"""
    repo_sync = RepoSync(CONFIG)
    return repo_sync.commit_and_push(commit_message)

def sync_repository():
    """Synchronize repository (pull then push)"""
    repo_sync = RepoSync(CONFIG)
    return repo_sync.sync_repo()

def check_repo_status():
    """Check repository status"""
    try:
        cmd = f"cd {CONFIG['local_path']} && git status --porcelain"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        
        if result.stdout.strip():
            logger.info("Repository has local changes:")
            for line in result.stdout.splitlines():
                logger.info(f"  {line}")
        else:
            logger.info("Repository is clean (no local changes)")
        
        # Check if we're behind/ahead of remote
        cmd = f"cd {CONFIG['local_path']} && git rev-list --count --left-right origin/{CONFIG['branch']}...HEAD"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        
        if result.stdout.strip():
            behind, ahead = result.stdout.strip().split('\t')
            
            if int(behind) > 0:
                logger.info(f"Repository is {behind} commit(s) behind remote")
            
            if int(ahead) > 0:
                logger.info(f"Repository is {ahead} commit(s) ahead of remote")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to check repository status: {e.stderr}")
        return False

def main():
    """Main entry point for command line usage"""
    parser = argparse.ArgumentParser(description="Repository Utility Functions")
    parser.add_argument('action', choices=['pull', 'push', 'sync', 'status'],
                        help='Action to perform on the repository')
    parser.add_argument('--message', '-m', help='Commit message for push action')
    
    args = parser.parse_args()
    
    # Check for GitHub token
    if not CONFIG.get("github_token"):
        logger.error("GitHub token not found. Set GITHUB_TOKEN environment variable.")
        sys.exit(1)
    
    # Execute requested action
    if args.action == 'pull':
        success = pull_repository()
    elif args.action == 'push':
        success = push_changes(args.message)
    elif args.action == 'sync':
        success = sync_repository()
    elif args.action == 'status':
        success = check_repo_status()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
EOL

    # Create README for automation tools
    cat > "$LOCAL_PATH/automation/README.md" << 'EOL'
# GitHub Repository Automation

This directory contains Python scripts for automating GitHub repository operations.

## Components

- **repo_sync.py**: Core module for repository synchronization
- **webhook_handler.py**: GitHub webhook handler
- **repo_utils.py**: Command-line utility functions

## Setup

1. Set required environment variables:
   ```bash
   export GITHUB_TOKEN=your_personal_access_token
   export WEBHOOK_SECRET=your_webhook_secret