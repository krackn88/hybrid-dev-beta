#!/usr/bin/env python3
"""
GitHub Polling Service
Automates GitHub repository updates using polling at regular intervals
"""
import os
import sys
import time
import json
import logging
import argparse
import subprocess
import threading
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("polling_service.log"),
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
    "poll_interval": int(os.environ.get("POLL_INTERVAL", 300)),  # seconds
    "github_token": os.environ.get("GITHUB_TOKEN"),
    "auto_commit": os.environ.get("AUTO_COMMIT", "true").lower() in ("true", "1", "yes"),
    "auto_commit_interval": int(os.environ.get("AUTO_COMMIT_INTERVAL", 30)),  # minutes
}

class GitHubPoller:
    """Service to poll GitHub for changes and update local repository"""
    
    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
        self.last_commit_sha = None
        self.last_auto_commit = datetime.now()
        
        # Ensure repository directory exists
        self.repo_path = Path(self.config["local_path"])
        self.repo_path.mkdir(parents=True, exist_ok=True)
        
        # Set up GitHub API headers
        self.github_headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.config["github_token"]:
            self.github_headers["Authorization"] = f"token {self.config['github_token']}"
    
    def get_latest_commit_sha(self):
        """Get the latest commit SHA for the specified branch"""
        url = f"https://api.github.com/repos/{self.config['repo_owner']}/{self.config['repo_name']}/branches/{self.config['branch']}"
        
        try:
            response = requests.get(url, headers=self.github_headers)
            response.raise_for_status()
            
            data = response.json()
            if "commit" in data and "sha" in data["commit"]:
                return data["commit"]["sha"]
            
            logger.error(f"Unexpected API response structure: {data}")
            return None
        except requests.RequestException as e:
            logger.error(f"Error getting latest commit: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            return None
    
    def clone_or_pull_repository(self):
        """Clone repository if it doesn't exist, otherwise pull latest changes"""
        git_dir = self.repo_path / ".git"
        
        if not git_dir.exists():
            logger.info(f"Cloning repository to {self.repo_path}")
            clone_url = f"https://{self.config['github_token']}@github.com/{self.config['repo_owner']}/{self.config['repo_name']}.git"
            
            try:
                subprocess.run(
                    ["git", "clone", clone_url, str(self.repo_path)],
                    check=True,
                    capture_output=True
                )
                logger.info("Repository cloned successfully")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error cloning repository: {e.stderr.decode()}")
                return False
        else:
            logger.info(f"Updating existing repository at {self.repo_path}")
            
            try:
                # Fetch and reset to origin/branch
                subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["git", "checkout", self.config["branch"]],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["git", "reset", "--hard", f"origin/{self.config['branch']}"],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True
                )
                
                logger.info("Repository updated successfully")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error updating repository: {e.stderr.decode()}")
                return False
    
    def run_post_update_actions(self):
        """Run actions after repository update"""
        # Check for VSCode extension
        vscode_dir = self.repo_path / "vscode-extension"
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
        if (self.repo_path / "requirements.txt").exists():
            logger.info("Installing Python dependencies")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True
                )
                logger.info("Python dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error installing Python dependencies: {e.stderr.decode()}")
    
    def auto_commit_changes(self):
        """Auto-commit and push local changes if enabled"""
        if not self.config["auto_commit"]:
            return
        
        # Check if auto-commit interval has passed
        now = datetime.now()
        if (now - self.last_auto_commit).total_seconds() < (self.config["auto_commit_interval"] * 60):
            return
        
        logger.info("Checking for local changes to commit")
        
        try:
            # Check if there are any changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                logger.info("No changes to commit")
                return
            
            # Add all changes
            subprocess.run(
                ["git", "add", "."],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True
            )
            
            # Create commit message with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Auto-commit: Updates [{timestamp}]"
            
            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True
            )
            
            # Push to GitHub
            push_url = f"https://{self.config['github_token']}@github.com/{self.config['repo_owner']}/{self.config['repo_name']}.git"
            subprocess.run(
                ["git", "push", push_url, self.config["branch"]],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True
            )
            
            logger.info("Changes committed and pushed successfully")
            self.last_auto_commit = now
        except subprocess.CalledProcessError as e:
            logger.error(f"Error during auto-commit: {e.stderr.decode() if e.stderr else str(e)}")
    
    def poll_and_update(self):
        """Poll GitHub for updates and update local repository if needed"""
        try:
            # Get latest commit SHA
            current_sha = self.get_latest_commit_sha()
            
            if not current_sha:
                logger.warning("Failed to get latest commit SHA, will retry next interval")
                return
            
            # If this is the first check or the SHA has changed
            if self.last_commit_sha is None or self.last_commit_sha != current_sha:
                logger.info(f"New commit detected: {current_sha}")
                
                # Update the repository
                if self.clone_or_pull_repository():
                    self.run_post_update_actions()
                    self.last_commit_sha = current_sha
            else:
                logger.info("No new commits detected")
                
                # Check for local changes to commit
                self.auto_commit_changes()
                
        except Exception as e:
            logger.error(f"Error in poll_and_update: {str(e)}")
    
    def start_polling(self):
        """Start the polling loop"""
        logger.info(f"Starting GitHub polling service")
        logger.info(f"Repository: {self.config['repo_owner']}/{self.config['repo_name']}")
        logger.info(f"Branch: {self.config['branch']}")
        logger.info(f"Local path: {self.config['local_path']}")
        logger.info(f"Poll interval: {self.config['poll_interval']} seconds")
        logger.info(f"Auto-commit: {self.config['auto_commit']}")
        if self.config["auto_commit"]:
            logger.info(f"Auto-commit interval: {self.config['auto_commit_interval']} minutes")
        
        # Initial update
        self.poll_and_update()
        
        try:
            # Polling loop
            while True:
                time.sleep(self.config["poll_interval"])
                self.poll_and_update()
        except KeyboardInterrupt:
            logger.info("Polling service stopped by user")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="GitHub Polling Service")
    parser.add_argument(
        "--poll-interval", 
        type=int, 
        default=CONFIG["poll_interval"],
        help=f"Polling interval in seconds (default: {CONFIG['poll_interval']})"
    )
    parser.add_argument(
        "--auto-commit", 
        action="store_true", 
        default=CONFIG["auto_commit"],
        help="Enable auto-commit of local changes"
    )
    parser.add_argument(
        "--auto-commit-interval", 
        type=int, 
        default=CONFIG["auto_commit_interval"],
        help=f"Auto-commit interval in minutes (default: {CONFIG['auto_commit_interval']})"
    )
    
    args = parser.parse_args()
    
    # Update config with command line arguments
    CONFIG["poll_interval"] = args.poll_interval
    CONFIG["auto_commit"] = args.auto_commit
    CONFIG["auto_commit_interval"] = args.auto_commit_interval
    
    return args

if __name__ == "__main__":
    args = parse_arguments()
    
    print(f"GitHub Polling Service v1.0.0")
    
    # Check for required environment variables
    if not CONFIG["github_token"]:
        logger.error("GITHUB_TOKEN environment variable is required")
        print("ERROR: GITHUB_TOKEN environment variable is required")
        print("Create a token at https://github.com/settings/tokens")
        print("Then set it with: export GITHUB_TOKEN=your_token_here")
        sys.exit(1)
    
    # Start polling service
    poller = GitHubPoller(CONFIG)
    poller.start_polling()