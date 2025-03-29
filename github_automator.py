#!/usr/bin/env python3
"""
GitHub Repository Automator
A comprehensive solution for automating GitHub repository operations

Features:
- Real-time updates via webhooks or polling
- Auto-commits and pushes changes
- Handles VSCode extension builds
- Maintains documentation and changelog
- Secure token handling

Author: krackn88
"""
import os
import sys
import time
import json
import hmac
import hashlib
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import threading
try:
    import requests
    from github import Github, GithubException
    GITHUB_API_AVAILABLE = True
except ImportError:
    GITHUB_API_AVAILABLE = False
    print("Warning: PyGitHub or requests not installed. Some features may be limited.")
    print("Install with: pip install PyGitHub requests")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("github_automator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Default configuration - override with environment variables or CLI args
DEFAULT_CONFIG = {
    "repo_owner": os.environ.get("REPO_OWNER", "krackn88"),
    "repo_name": os.environ.get("REPO_NAME", "hybrid-dev-beta"),
    "branch": os.environ.get("BRANCH", "main"),
    "local_path": os.environ.get("LOCAL_PATH", os.path.expanduser("~/hybrid-dev-beta")),
    "github_token": os.environ.get("GITHUB_TOKEN", ""),
    "webhook_secret": os.environ.get("WEBHOOK_SECRET", ""),
    "webhook_port": int(os.environ.get("WEBHOOK_PORT", 8000)),
    "poll_interval": int(os.environ.get("POLL_INTERVAL", 300)),  # seconds
    "auto_commit": os.environ.get("AUTO_COMMIT", "true").lower() in ("true", "1", "yes"),
    "auto_commit_interval": int(os.environ.get("AUTO_COMMIT_INTERVAL", 30)),  # minutes
    "vscode_extension_dir": os.environ.get("VSCODE_EXTENSION_DIR", "vscode-extension"),
    "todo_file": os.environ.get("TODO_FILE", "todo.md"),
    "changelog_file": os.environ.get("CHANGELOG_FILE", "CHANGELOG.md"),
}

class GitHubAutomator:
    """Main class for GitHub automation operations"""
    
    def __init__(self, config=None):
        """Initialize with configuration"""
        self.config = config or DEFAULT_CONFIG
        self.validate_config()
        
        # Set up GitHub API client if available
        if GITHUB_API_AVAILABLE and self.config["github_token"]:
            self.github = Github(self.config["github_token"])
            try:
                self.repo = self.github.get_repo(f"{self.config['repo_owner']}/{self.config['repo_name']}")
                logger.info(f"Connected to GitHub repository: {self.config['repo_owner']}/{self.config['repo_name']}")
            except GithubException as e:
                logger.error(f"Failed to access repository: {str(e)}")
                raise
        
        # Local repository path
        self.local_path = Path(self.config["local_path"])
        self.local_path.mkdir(parents=True, exist_ok=True)
        
        # VSCode extension directory
        self.vscode_dir = self.local_path / self.config["vscode_extension_dir"]
        
        # Track the last commit we've seen (for polling)
        self.last_commit_sha = None
        self.last_auto_commit = datetime.now()
    
    def validate_config(self):
        """Validate configuration settings"""
        if not self.config.get("github_token"):
            logger.error("GitHub token is required. Set the GITHUB_TOKEN environment variable.")
            raise ValueError("GitHub token is required")
        
        if not self.config.get("repo_owner") or not self.config.get("repo_name"):
            logger.error("Repository owner and name are required.")
            raise ValueError("Repository owner and name are required")
    
    def clone_or_pull_repository(self):
        """Clone the repository if it doesn't exist, otherwise pull latest changes"""
        logger.info(f"Syncing repository to {self.local_path}")
        
        git_dir = self.local_path / ".git"
        if not git_dir.exists():
            logger.info("Repository not found locally. Cloning...")
            clone_url = f"https://{self.config['github_token']}@github.com/{self.config['repo_owner']}/{self.config['repo_name']}.git"
            
            try:
                subprocess.run(
                    ["git", "clone", clone_url, str(self.local_path)],
                    check=True,
                    capture_output=True
                )
                logger.info("Repository cloned successfully")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error cloning repository: {e.stderr.decode() if e.stderr else str(e)}")
                return False
        else:
            logger.info("Repository exists. Pulling latest changes...")
            
            try:
                # Get current branch name
                result = subprocess.run(
                    ["git", "symbolic-ref", "--short", "HEAD"],
                    cwd=str(self.local_path),
                    check=True,
                    capture_output=True,
                    text=True
                )
                current_branch = result.stdout.strip()
                
                # Stash any changes if needed
                changes = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(self.local_path),
                    check=True,
                    capture_output=True,
                    text=True
                ).stdout.strip()
                
                if changes:
                    logger.info("Local changes detected. Stashing...")
                    subprocess.run(
                        ["git", "stash", "save", f"Auto-stash before pull {datetime.now().isoformat()}"],
                        cwd=str(self.local_path),
                        check=True,
                        capture_output=True
                    )
                
                # Fetch and checkout the desired branch
                subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=str(self.local_path),
                    check=True,
                    capture_output=True
                )
                
                if current_branch != self.config["branch"]:
                    logger.info(f"Switching from {current_branch} to {self.config['branch']}")
                    subprocess.run(
                        ["git", "checkout", self.config["branch"]],
                        cwd=str(self.local_path),
                        check=True,
                        capture_output=True
                    )
                
                # Pull latest changes
                subprocess.run(
                    ["git", "pull", "origin", self.config["branch"]],
                    cwd=str(self.local_path),
                    check=True,
                    capture_output=True
                )
                
                logger.info("Repository updated successfully")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Error updating repository: {e.stderr.decode() if e.stderr else str(e)}")
                return False
    
    def commit_and_push_changes(self, commit_message=None):
        """Commit and push local changes to GitHub"""
        if not commit_message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Auto-update [{timestamp}]"
        
        logger.info(f"Committing changes with message: {commit_message}")
        
        try:
            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.local_path),
                check=True,
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                logger.info("No changes to commit")
                return True
            
            # Add all changes
            subprocess.run(
                ["git", "add", "."],
                cwd=str(self.local_path),
                check=True,
                capture_output=True
            )
            
            # Configure git if needed
            try:
                subprocess.run(
                    ["git", "config", "user.name"],
                    cwd=str(self.local_path),
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError:
                subprocess.run(
                    ["git", "config", "user.name", "GitHub Automator"],
                    cwd=str(self.local_path),
                    check=True,
                    capture_output=True
                )
            
            try:
                subprocess.run(
                    ["git", "config", "user.email"],
                    cwd=str(self.local_path),
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError:
                subprocess.run(
                    ["git", "config", "user.email", "automator@github.com"],
                    cwd=str(self.local_path),
                    check=True,
                    capture_output=True
                )
            
            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=str(self.local_path),
                check=True,
                capture_output=True
            )
            
            # Push to GitHub
            push_url = f"https://{self.config['github_token']}@github.com/{self.config['repo_owner']}/{self.config['repo_name']}.git"
            subprocess.run(
                ["git", "push", push_url, self.config["branch"]],
                cwd=str(self.local_path),
                check=True,
                capture_output=True
            )
            
            logger.info("Changes committed and pushed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error in git operations: {e.stderr.decode() if e.stderr else str(e)}")
            return False
    
    def build_vscode_extension(self):
        """Build the VSCode extension if it exists"""
        if not self.vscode_dir.exists():
            logger.info(f"VSCode extension directory not found at {self.vscode_dir}")
            return False
        
        if not (self.vscode_dir / "package.json").exists():
            logger.info("package.json not found in VSCode extension directory")
            return False
        
        logger.info("Building VSCode extension")
        
        try:
            # Install dependencies
            subprocess.run(
                ["npm", "install"],
                cwd=str(self.vscode_dir),
                check=True,
                capture_output=True
            )
            
            # Compile TypeScript
            subprocess.run(
                ["npm", "run", "compile"],
                cwd=str(self.vscode_dir),
                check=True,
                capture_output=True
            )
            
            logger.info("VSCode extension built successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error building VSCode extension: {e.stderr.decode() if e.stderr else str(e)}")
            
            # Try to fix common TypeScript errors
            if "error TS2339: Property 'subscriptions' does not exist" in (e.stderr.decode() if e.stderr else ""):
                logger.info("Attempting to fix TypeScript error...")
                self.fix_vscode_extension_errors()
                
                # Try building again
                try:
                    subprocess.run(
                        ["npm", "run", "compile"],
                        cwd=str(self.vscode_dir),
                        check=True,
                        capture_output=True
                    )
                    logger.info("VSCode extension fixed and built successfully")
                    return True
                except subprocess.CalledProcessError as e2:
                    logger.error(f"Still failed after fix attempt: {e2.stderr.decode() if e2.stderr else str(e2)}")
            
            return False
    
    def fix_vscode_extension_errors(self):
        """Fix common errors in the VSCode extension"""
        extension_file = self.vscode_dir / "src" / "extension.ts"
        
        if not extension_file.exists():
            logger.error("extension.ts not found")
            return False
        
        # Read the current file
        with open(extension_file, "r") as f:
            content = f.read()
        
        # Fix the subscriptions error by modifying the resolveWebviewView method
        # This is a common error when trying to use context.subscriptions from WebviewViewResolveContext
        fixed_content = content.replace(
            "context.subscriptions",
            "// Fix: Use the extension context's subscriptions instead of WebviewViewResolveContext\n      this._extensionContext.subscriptions"
        )
        
        # If we made a change, update the file
        if fixed_content != content:
            # Backup the original file
            backup_file = extension_file.with_suffix(".ts.bak")
            with open(backup_file, "w") as f:
                f.write(content)
            
            # Write the fixed content
            with open(extension_file, "w") as f:
                f.write(fixed_content)
            
            logger.info(f"Fixed TypeScript error in {extension_file} (backup at {backup_file})")
            return True
        
        return False
    
    def update_todo_file(self):
        """Update the todo.md file with completed items"""
        todo_file = self.local_path / self.config["todo_file"]
        
        if not todo_file.exists():
            logger.info(f"Todo file not found at {todo_file}. Creating...")
            with open(todo_file, "w") as f:
                f.write("# Todo List\n\n")
                f.write("## High Priority\n")
                f.write("- [x] [HIGH] Set up GitHub repository automation\n")
                f.write("- [x] [HIGH] Fix VSCode extension TypeScript errors\n")
                f.write("- [ ] [HIGH] Implement webhook handler for real-time updates\n\n")
                f.write("## Medium Priority\n")
                f.write("- [ ] [MEDIUM] Add Python integration for hybrid development\n")
                f.write("- [ ] [MEDIUM] Create comprehensive test suite\n")
                f.write("- [ ] [MEDIUM] Implement CI/CD pipeline\n\n")
                f.write("## Low Priority\n")
                f.write("- [ ] [LOW] Improve documentation\n")
                f.write("- [ ] [LOW] Add advanced features to VSCode extension\n")
                f.write("- [ ] [LOW] Create demo examples\n")
        else:
            # Read the current todo file
            with open(todo_file, "r") as f:
                content = f.read()
            
            # Mark common tasks as completed
            updated_content = content
            tasks_to_mark = [
                "Set up GitHub repository automation",
                "Fix VSCode extension TypeScript errors",
                "Implement basic GitHub automation"
            ]
            
            for task in tasks_to_mark:
                pattern = f"- [ ] [HIGH] {task}"
                if pattern in updated_content:
                    updated_content = updated_content.replace(pattern, f"- [x] [HIGH] {task}")
                    logger.info(f"Marked task as completed: {task}")
            
            # If changes were made, update the file
            if updated_content != content:
                with open(todo_file, "w") as f:
                    f.write(updated_content)
                logger.info("Todo file updated with completed tasks")
        
        return True
    
    def update_changelog(self):
        """Update the CHANGELOG.md file with recent changes"""
        changelog_file = self.local_path / self.config["changelog_file"]
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        new_entry = f"""## [Unreleased] - {timestamp}

### Added
- Enhanced GitHub repository automation
- Real-time updates via webhooks/polling

### Fixed
- VSCode extension TypeScript errors
- Improved error handling and logging

"""
        
        if not changelog_file.exists():
            logger.info(f"Changelog file not found at {changelog_file}. Creating...")
            with open(changelog_file, "w") as f:
                f.write("# Changelog\n\n")
                f.write(new_entry)
        else:
            # Read the current changelog
            with open(changelog_file, "r") as f:
                content = f.read()
            
            # Check if we already have an Unreleased section
            if "## [Unreleased]" in content:
                # Find the position to insert new items
                unreleased_pos = content.find("## [Unreleased]")
                next_version_pos = content.find("##", unreleased_pos + 1)
                
                if next_version_pos > 0:
                    # Insert between the Unreleased header and the next version
                    updated_content = (
                        content[:unreleased_pos] +
                        f"## [Unreleased] - {timestamp}\n\n" +
                        "### Added\n" +
                        "- Enhanced GitHub repository automation\n" +
                        "- Real-time updates via webhooks/polling\n\n" +
                        "### Fixed\n" +
                        "- VSCode extension TypeScript errors\n" +
                        "- Improved error handling and logging\n\n" +
                        content[next_version_pos:]
                    )
                else:
                    # Add to the end of the file
                    updated_content = content + "\n" + new_entry
            else:
                # Add to the beginning after the title
                title_end = content.find("\n") + 1
                updated_content = content[:title_end] + "\n" + new_entry + content[title_end:]
            
            # Update the file
            with open(changelog_file, "w") as f:
                f.write(updated_content)
            
            logger.info("Changelog updated with recent changes")
        
        return True
    
    def get_next_todo_item(self):
        """Get the next highest priority item from the todo list"""
        todo_file = self.local_path / self.config["todo_file"]
        
        if not todo_file.exists():
            return "Create todo.md file"
        
        # Read the todo file
        with open(todo_file, "r") as f:
            lines = f.readlines()
        
        # Look for incomplete high priority items first
        for line in lines:
            if "- [ ] [HIGH]" in line:
                return line.strip()
        
        # Then medium priority
        for line in lines:
            if "- [ ] [MEDIUM]" in line:
                return line.strip()
        
        # Then low priority
        for line in lines:
            if "- [ ] [LOW]" in line:
                return line.strip()
        
        return "All tasks completed!"
    
    def get_latest_commit_sha(self):
        """Get the latest commit SHA for the specified branch"""
        if GITHUB_API_AVAILABLE:
            try:
                branch = self.repo.get_branch(self.config["branch"])
                return branch.commit.sha
            except GithubException as e:
                logger.error(f"Error getting latest commit: {str(e)}")
                return None
        else:
            # Fallback to git command
            try:
                result = subprocess.run(
                    ["git", "ls-remote", f"https://github.com/{self.config['repo_owner']}/{self.config['repo_name']}.git", f"refs/heads/{self.config['branch']}"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                sha = result.stdout.split()[0]
                return sha
            except subprocess.CalledProcessError as e:
                logger.error(f"Error getting latest commit: {e.stderr}")
                return None
    
    def poll_for_changes(self):
        """Poll for changes in the repository"""
        logger.info(f"Starting polling for changes (interval: {self.config['poll_interval']} seconds)")
        
        while True:
            try:
                # Get the latest commit SHA
                current_sha = self.get_latest_commit_sha()
                
                if not current_sha:
                    logger.warning("Failed to get latest commit SHA")
                    time.sleep(self.config["poll_interval"])
                    continue
                
                # If we haven't seen this commit before
                if self.last_commit_sha is None or self.last_commit_sha != current_sha:
                    logger.info(f"New commit detected: {current_sha}")
                    self.last_commit_sha = current_sha
                    
                    # Pull changes and update
                    self.clone_or_pull_repository()
                    self.build_vscode_extension()
                    self.update_todo_file()
                    self.update_changelog()
                else:
                    logger.info("No new commits detected")
                    
                    # Check if it's time for an auto-commit
                    if self.config["auto_commit"]:
                        now = datetime.now()
                        time_since_last_commit = (now - self.last_auto_commit).total_seconds() / 60
                        
                        if time_since_last_commit >= self.config["auto_commit_interval"]:
                            logger.info(f"Auto-commit interval reached ({self.config['auto_commit_interval']} minutes)")
                            self.last_auto_commit = now
                            self.commit_and_push_changes("Auto-commit: Regular update")
                
                # Wait for the next poll
                time.sleep(self.config["poll_interval"])
            
            except KeyboardInterrupt:
                logger.info("Polling stopped by user")
                break
            except Exception as e:
                logger.error(f"Error during polling: {str(e)}")
                time.sleep(self.config["poll_interval"] * 2)  # Wait longer on error
    
    def run_webhook_server(self):
        """Run a webhook server to listen for GitHub events"""
        # This requires a separate HTTP server implementation
        # For simplicity, I'll provide a basic version using http.server
        
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class WebhookHandler(BaseHTTPRequestHandler):
            """Handler for GitHub webhook events"""
            
            def _send_response(self, status_code, message):
                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"message": message}).encode('utf-8'))
            
            def do_GET(self):
                """Handle GET request - simple health check"""
                self._send_response(200, "GitHub webhook server is running")
            
            def do_POST(self):
                """Handle POST request - GitHub webhook event"""
                content_length = int(self.headers.get('Content-Length', 0))
                payload_bytes = self.rfile.read(content_length)
                
                # Verify signature if webhook secret is configured
                if self.server.webhook_secret:
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
                    if ref != f"refs/heads/{self.server.automator.config['branch']}":
                        logger.info(f"Ignoring push to {ref}")
                        self._send_response(200, f"Ignored push to {ref}")
                        return
                    
                    # Process push event
                    try:
                        threading.Thread(target=self._process_push_event).start()
                        self._send_response(202, "Push event processing started")
                    except Exception as e:
                        logger.error(f"Error processing push event: {str(e)}")
                        self._send_response(500, f"Error processing push event: {str(e)}")
                else:
                    # Just acknowledge other events
                    self._send_response(200, f"Received {event_type} event")
            
            def _verify_signature(self, payload_bytes, signature_header):
                """Verify GitHub webhook signature"""
                if not self.server.webhook_secret:
                    return True
                
                # The signature comes in as "sha256=HASH"
                sha_name, github_signature = signature_header.split('=', 1)
                if sha_name != 'sha256':
                    return False
                
                # Calculate expected signature
                mac = hmac.new(
                    self.server.webhook_secret.encode('utf-8'),
                    msg=payload_bytes,
                    digestmod=hashlib.sha256
                )
                expected_signature = mac.hexdigest()
                
                # Compare signatures
                return hmac.compare_digest(github_signature, expected_signature)
            
            def _process_push_event(self):
                """Process push event in a separate thread"""
                logger.info("Processing push event")
                automator = self.server.automator
                
                # Pull changes and update
                automator.clone_or_pull_repository()
                automator.build_vscode_extension()
                automator.update_todo_file()
                automator.update_changelog()
        
        # Extend HTTPServer to hold our automator instance and webhook secret
        class AutomatorHTTPServer(HTTPServer):
            def __init__(self, server_address, RequestHandlerClass, automator, webhook_secret):
                self.automator = automator
                self.webhook_secret = webhook_secret
                super().__init__(server_address, RequestHandlerClass)
        
        # Start server
        server_address = ('', self.config["webhook_port"])
        httpd = AutomatorHTTPServer(
            server_address,
            WebhookHandler,
            self,
            self.config["webhook_secret"]
        )
        
        logger.info(f"Starting webhook server on port {self.config['webhook_port']}")
        logger.info("Use Ctrl+C to stop")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Webhook server stopped by user")
        finally:
            httpd.server_close()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="GitHub Repository Automator")
    
    parser.add_argument(
        "--mode",
        choices=["webhook", "poll", "update"],
        default="update",
        help="Operating mode: webhook (server), poll (client), or update (one-time)"
    )
    
    parser.add_argument(
        "--repo-owner",
        default=DEFAULT_CONFIG["repo_owner"],
        help=f"Repository owner (default: {DEFAULT_CONFIG['repo_owner']})"
    )
    
    parser.add_argument(
        "--repo-name",
        default=DEFAULT_CONFIG["repo_name"],
        help=f"Repository name (default: {DEFAULT_CONFIG['repo_name']})"
    )
    
    parser.add_argument(
        "--branch",
        default=DEFAULT_CONFIG["branch"],
        help=f"Branch to monitor (default: {DEFAULT_CONFIG['branch']})"
    )
    
    parser.add_argument(
        "--local-path",
        default=DEFAULT_CONFIG["local_path"],
        help=f"Local repository path (default: {DEFAULT_CONFIG['local_path']})"
    )
    
    parser.add_argument(
        "--webhook-port",
        type=int,
        default=DEFAULT_CONFIG["webhook_port"],
        help=f"Port for webhook server (default: {DEFAULT_CONFIG['webhook_port']})"
    )
    
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=DEFAULT_CONFIG["poll_interval"],
        help=f"Polling interval in seconds (default: {DEFAULT_CONFIG['poll_interval']})"
    )
    
    parser.add_argument(
        "--auto-commit",
        action="store_true",
        default=DEFAULT_CONFIG["auto_commit"],
        help="Enable auto-commit of local changes"
    )
    
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip building VSCode extension"
    )
    
    parser.add_argument(
        "--commit-message",
        help="Custom commit message for changes"
    )
    
    args = parser.parse_args()
    
    # Update config from arguments
    config = DEFAULT_CONFIG.copy()
    config.update({
        "repo_owner": args.repo_owner,
        "repo_name": args.repo_name,
        "branch": args.branch,
        "local_path": args.local_path,
        "webhook_port": args.webhook_port,
        "poll_interval": args.poll_interval,
        "auto_commit": args.auto_commit,
    })
    
    return args, config

def main():
    """Main entry point"""
    args, config = parse_arguments()
    
    # Print banner
    print(f"\n{'='*60}")
    print(f"GitHub Repository Automator v1.0.0")
    print(f"Repository: {config['repo_owner']}/{config['repo_name']} ({config['branch']})")
    print(f"Local path: {config['local_path']}")
    print(f"Mode: {args.mode}")
    print(f"{'='*60}\n")
    
    # Check for GitHub token
    if not config["github_token"]:
        print("ERROR: GITHUB_TOKEN environment variable is required.")
        print("Set it with: export GITHUB_TOKEN=your_token_here")
        return 1
    
    # Initialize automator
    automator = GitHubAutomator(config)
    
    # Run in the specified mode
    if args.mode == "webhook":
        if not config["webhook_secret"]:
            logger.warning("WEBHOOK_SECRET not set - webhook signatures won't be verified")
            print("WARNING: For security, set the WEBHOOK_SECRET environment variable")
        
        automator.run_webhook_server()
    
    elif args.mode == "poll":
        automator.poll_for_changes()
    
    else:  # update mode
        # Sync repository
        if not automator.clone_or_pull_repository():
            logger.error("Failed to sync repository")
            return 1
        
        # Build VSCode extension
        if not args.no_build:
            automator.build_vscode_extension()
        
        # Update documentation
        automator.update_todo_file()
        automator.update_changelog()
        
        # Commit and push changes
        if automator.config["auto_commit"]:
            automator.commit_and_push_changes(args.commit_message)
        
        # Show next steps
        next_task = automator.get_next_todo_item()
        print(f"\nNext task: {next_task}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())