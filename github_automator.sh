#!/bin/bash

# github_automator.sh - Automate GitHub repository updates
# This script provides utilities for monitoring and automating actions on GitHub repositories
# Author: krackn88

set -e  # Exit immediately if a command exits with a non-zero status

# --- Constants and Configuration ---
LOG_FILE="github_automation.log"
CONFIG_FILE=".github_automator_config"
POLLING_INTERVAL=300  # Default polling interval in seconds (5 minutes)
MAX_RETRIES=3
RETRY_DELAY=5

# --- Logging Functions ---
log_info() {
    echo "[INFO] $(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

log_error() {
    echo "[ERROR] $(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

log_warning() {
    echo "[WARNING] $(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

# --- Setup Functions ---
check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check for required tools
    for cmd in gh jq curl python3; do
        if ! command -v $cmd &> /dev/null; then
            log_error "$cmd is required but not installed. Please install it to continue."
            exit 1
        fi
    done
    
    # Check for GitHub CLI authentication
    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI not authenticated. Please run 'gh auth login' first or set GITHUB_TOKEN."
        exit 1
    fi
    
    log_info "All dependencies are met."
}

setup_environment() {
    log_info "Setting up environment..."
    
    # Create config file if it doesn't exist
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "POLLING_INTERVAL=$POLLING_INTERVAL" > $CONFIG_FILE
        echo "# Add your repository details below" >> $CONFIG_FILE
        echo "REPO_OWNER=$(gh repo view --json owner -q .owner.login)" >> $CONFIG_FILE
        echo "REPO_NAME=$(gh repo view --json name -q .name)" >> $CONFIG_FILE
        echo "WEBHOOK_ENABLED=false" >> $CONFIG_FILE
        log_info "Created default configuration file: $CONFIG_FILE"
    fi
    
    # Load configuration
    source $CONFIG_FILE
    
    # Validate GitHub token from environment
    if [ -z "$GITHUB_TOKEN" ] && [ -z "$GH_TOKEN" ]; then
        log_warning "No GitHub token found in environment variables. Using GitHub CLI authentication."
        # Try to get token from gh cli
        GH_TOKEN=$(gh auth token)
        if [ -z "$GH_TOKEN" ]; then
            log_error "Failed to get GitHub token from CLI. Please set GITHUB_TOKEN environment variable."
            exit 1
        fi
        export GITHUB_TOKEN=$GH_TOKEN
    fi
    
    log_info "Environment setup completed."
}

setup_webhook() {
    log_info "Setting up webhook for real-time updates..."
    
    if [ "$WEBHOOK_ENABLED" != "true" ]; then
        log_info "Webhooks are disabled in config. Skipping setup."
        return 0
    fi
    
    # Check if webhook secret is configured
    if [ -z "$WEBHOOK_SECRET" ]; then
        WEBHOOK_SECRET=$(openssl rand -hex 20)
        echo "WEBHOOK_SECRET=$WEBHOOK_SECRET" >> $CONFIG_FILE
        log_info "Generated new webhook secret"
    fi
    
    # Create webhook using GitHub API
    WEBHOOK_URL=${WEBHOOK_URL:-"https://example.com/webhook"}  # Default placeholder, should be set in config
    
    log_info "Creating webhook pointing to: $WEBHOOK_URL"
    
    response=$(curl -s -X POST \
      -H "Authorization: token $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github.v3+json" \
      "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks" \
      -d '{
        "name": "web",
        "active": true,
        "events": ["push", "pull_request", "issues", "issue_comment"],
        "config": {
          "url": "'"$WEBHOOK_URL"'",
          "content_type": "json",
          "secret": "'"$WEBHOOK_SECRET"'",
          "insecure_ssl": "0"
        }
      }')
    
    if echo "$response" | jq -e '.id' &> /dev/null; then
        hook_id=$(echo "$response" | jq '.id')
        log_info "Webhook created successfully with ID: $hook_id"
        echo "WEBHOOK_ID=$hook_id" >> $CONFIG_FILE
    else
        log_error "Failed to create webhook: $(echo "$response" | jq -r '.message')"
        log_warning "Will fall back to polling method"
    fi
}

# --- Monitoring Functions ---
poll_repository() {
    log_info "Starting repository polling (interval: ${POLLING_INTERVAL}s)..."
    
    # Track last checked timestamps
    last_commit_check=$(date +%s)
    last_pr_check=$(date +%s)
    last_issue_check=$(date +%s)
    
    while true; do
        # Check for new commits
        check_for_new_commits "$last_commit_check"
        last_commit_check=$(date +%s)
        
        # Check for new or updated PRs
        check_for_pull_requests "$last_pr_check"
        last_pr_check=$(date +%s)
        
        # Check for new or updated issues
        check_for_issues "$last_issue_check"
        last_issue_check=$(date +%s)
        
        log_info "Sleeping for $POLLING_INTERVAL seconds..."
        sleep $POLLING_INTERVAL
    done
}

check_for_new_commits() {
    local since=$1
    local since_date=$(date -u -d "@$since" +'%Y-%m-%dT%H:%M:%SZ')
    
    log_info "Checking for new commits since $since_date"
    
    for attempt in $(seq 1 $MAX_RETRIES); do
        commits=$(gh api \
            repos/$REPO_OWNER/$REPO_NAME/commits \
            --method GET \
            -f since="$since_date" \
            -q '.[] | {sha: .sha, message: .commit.message, author: .commit.author.name, date: .commit.author.date}' 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            if [ -n "$commits" ]; then
                log_info "Found new commits:"
                echo "$commits" | jq -r '. | "- \(.sha[0:7]) \(.date): \(.message | split("\n")[0])"' | tee -a $LOG_FILE
                
                # Execute handlers for new commits
                handle_new_commits "$commits"
            else
                log_info "No new commits found"
            fi
            break
        else
            log_warning "Attempt $attempt: Failed to fetch commits. Retrying in $RETRY_DELAY seconds..."
            sleep $RETRY_DELAY
        fi
    done
}

check_for_pull_requests() {
    local since=$1
    local since_date=$(date -u -d "@$since" +'%Y-%m-%dT%H:%M:%SZ')
    
    log_info "Checking for pull request activity since $since_date"
    
    prs=$(gh pr list --json number,title,url,updatedAt,author --search "updated:>=$since_date" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ "$(echo "$prs" | jq '. | length')" -gt 0 ]; then
        log_info "Found PR activity:"
        echo "$prs" | jq -r '.[] | "- #\(.number): \(.title) by \(.author.login) (\(.url))"' | tee -a $LOG_FILE
        
        # Execute handlers for PR updates
        handle_pull_requests "$prs"
    else
        log_info "No PR activity found"
    fi
}

check_for_issues() {
    local since=$1
    local since_date=$(date -u -d "@$since" +'%Y-%m-%dT%H:%M:%SZ')
    
    log_info "Checking for issue activity since $since_date"
    
    issues=$(gh issue list --json number,title,url,updatedAt,author --search "updated:>=$since_date" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ "$(echo "$issues" | jq '. | length')" -gt 0 ]; then
        log_info "Found issue activity:"
        echo "$issues" | jq -r '.[] | "- #\(.number): \(.title) by \(.author.login) (\(.url))"' | tee -a $LOG_FILE
        
        # Execute handlers for issue updates
        handle_issues "$issues"
    else
        log_info "No issue activity found"
    fi
}

# --- Action Handlers ---
handle_new_commits() {
    local commits=$1
    log_info "Processing new commits..."
    
    # Example: Run CI checks or deployment for new commits
    # This is a placeholder where you can add custom logic
    
    # Example: Run Python script to process commits
    if [ -f "scripts/process_commits.py" ]; then
        log_info "Running commit processor script"
        echo "$commits" | python3 scripts/process_commits.py
    fi
}

handle_pull_requests() {
    local prs=$1
    log_info "Processing pull request updates..."
    
    # Example: Auto-label PRs based on content
    if [ -f "scripts/label_prs.py" ]; then
        log_info "Running PR labeling script"
        echo "$prs" | python3 scripts/label_prs.py
    fi
}

handle_issues() {
    local issues=$1
    log_info "Processing issue updates..."
    
    # Example: Auto-assign issues or add labels
    if [ -f "scripts/process_issues.py" ]; then
        log_info "Running issue processor script"
        echo "$issues" | python3 scripts/process_issues.py
    fi
}

# --- Utility Functions ---
create_action_workflow() {
    log_info "Creating GitHub Action workflow file..."
    
    mkdir -p .github/workflows
    
    cat > .github/workflows/github_automator.yml << 'EOF'
name: GitHub Repository Automator

on:
  schedule:
    - cron: '*/15 * * * *'  # Run every 15 minutes
  push:
    branches: [ main ]
  pull_request:
    types: [opened, synchronize, reopened, closed]
  issues:
    types: [opened, edited, closed, reopened]
  issue_comment:
    types: [created, edited]

jobs:
  automate:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pygithub pyyaml requests
        
    - name: Run automation script
      run: |
        chmod +x ./github_automator.sh
        ./github_automator.sh action
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
EOF
    
    log_info "GitHub Action workflow created at .github/workflows/github_automator.yml"
}

create_python_handler() {
    log_info "Creating Python handler script template..."
    
    mkdir -p scripts
    
    cat > scripts/github_automation.py << 'EOF'
#!/usr/bin/env python3
"""
GitHub Automation Helper

This script provides functions for processing GitHub events and automating
repository tasks using PyGitHub.
"""

import os
import sys
import json
import logging
from datetime import datetime
from github import Github, GithubException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("github_automation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("github-automation")

# Initialize GitHub API client
def get_github_client():
    """Initialize and return a GitHub client using token authentication."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        logger.error("No GitHub token found in environment variables")
        sys.exit(1)
    
    return Github(token)

def process_commits(commits_json):
    """Process new commits from JSON input."""
    try:
        commits = json.loads(commits_json)
        logger.info(f"Processing {len(commits)} commits")
        
        # Add your custom logic here
        for commit in commits:
            logger.info(f"Processing commit: {commit['sha']}")
            # Example: Analyze commit message for keywords and trigger actions
            
    except Exception as e:
        logger.error(f"Error processing commits: {str(e)}")

def label_pull_requests(prs_json):
    """Auto-label pull requests based on content."""
    try:
        g = get_github_client()
        prs = json.loads(prs_json)
        
        repo_name = os.environ.get("GITHUB_REPOSITORY", "")
        if not repo_name:
            logger.error("GITHUB_REPOSITORY environment variable not set")
            return
        
        repo = g.get_repo(repo_name)
        
        for pr_data in prs:
            pr_number = pr_data["number"]
            pr = repo.get_pull(pr_number)
            
            # Example: Label based on files changed
            files_changed = list(pr.get_files())
            
            if any(f.filename.endswith(".py") for f in files_changed):
                pr.add_to_labels("python")
            
            if any(f.filename.endswith((".js", ".ts")) for f in files_changed):
                pr.add_to_labels("javascript")
                
            # Check PR size and add appropriate label
            total_changes = sum(f.changes for f in files_changed)
            if total_changes > 500:
                pr.add_to_labels("large-change")
            elif total_changes < 50:
                pr.add_to_labels("small-change")
                
    except Exception as e:
        logger.error(f"Error labeling PRs: {str(e)}")

def process_issues(issues_json):
    """Process and categorize issues."""
    try:
        g = get_github_client()
        issues = json.loads(issues_json)
        
        repo_name = os.environ.get("GITHUB_REPOSITORY", "")
        if not repo_name:
            logger.error("GITHUB_REPOSITORY environment variable not set")
            return
        
        repo = g.get_repo(repo_name)
        
        for issue_data in issues:
            issue_number = issue_data["number"]
            issue = repo.get_issue(issue_number)
            
            # Auto-assign based on content keywords
            title = issue.title.lower()
            body = issue.body.lower() if issue.body else ""
            
            # Example: Auto-label based on content
            if "bug" in title or "error" in title or "crash" in title:
                issue.add_to_labels("bug")
            
            if "feature" in title or "enhancement" in title:
                issue.add_to_labels("enhancement")
                
            # Auto-assign to team members based on area
            if "frontend" in title or "ui" in title:
                try:
                    issue.add_to_assignees("frontend-team-member")
                except GithubException:
                    logger.warning(f"Could not assign issue #{issue_number}")
                    
    except Exception as e:
        logger.error(f"Error processing issues: {str(e)}")

if __name__ == "__main__":
    # Script can be called with different modes
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == "commits":
            process_commits(sys.stdin.read())
        elif mode == "prs":
            label_pull_requests(sys.stdin.read())
        elif mode == "issues":
            process_issues(sys.stdin.read())
        else:
            logger.error(f"Unknown mode: {mode}")
    else:
        logger.error("No mode specified")
EOF
    
    chmod +x scripts/github_automation.py
    log_info "Created Python handler script at scripts/github_automation.py"
}

# --- Main Entry Point ---
main() {
    log_info "Starting GitHub Automator v1.0.0"
    
    # Initialize log file
    > $LOG_FILE
    
    # Process command line arguments
    case "$1" in
        setup)
            check_dependencies
            setup_environment
            setup_webhook
            create_action_workflow
            create_python_handler
            log_info "Setup completed successfully"
            ;;
        poll)
            check_dependencies
            setup_environment
            poll_repository
            ;;
        action)
            # Mode for running inside GitHub Action
            check_dependencies
            setup_environment
            log_info "Running in GitHub Action mode"
            
            # Check if we were triggered by a specific event
            event_name=${GITHUB_EVENT_NAME:-"manual"}
            log_info "Triggered by: $event_name"
            
            # Process the event that triggered this run
            case "$event_name" in
                push)
                    check_for_new_commits "$(date -d '1 hour ago' +%s)"
                    ;;
                pull_request|pull_request_target)
                    check_for_pull_requests "$(date -d '1 hour ago' +%s)"
                    ;;
                issues|issue_comment)
                    check_for_issues "$(date -d '1 hour ago' +%s)"
                    ;;
                schedule|workflow_dispatch|manual)
                    # Check everything when running on schedule or manually
                    check_for_new_commits "$(date -d '1 hour ago' +%s)"
                    check_for_pull_requests "$(date -d '1 hour ago' +%s)"
                    check_for_issues "$(date -d '1 hour ago' +%s)"
                    ;;
            esac
            ;;
        webhook)
            # Process incoming webhook (to be run by web server)
            log_info "Processing webhook payload from stdin"
            payload=$(cat)
            echo "$payload" > /tmp/github_webhook_payload.json
            
            # Verify webhook signature (in a real implementation)
            # process_webhook_payload "$payload"
            
            log_info "Webhook processed"
            ;;
        help|--help|-h)
            echo "GitHub Automator - Automate GitHub repository updates"
            echo ""
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  setup    - Set up automation (config, webhook, GitHub Action)"
            echo "  poll     - Start polling for repository changes"
            echo "  action   - Run automation (for use in GitHub Actions)"
            echo "  webhook  - Process webhook payload from stdin"
            echo "  help     - Show this help message"
            ;;
        *)
            log_info "No command specified, running setup..."
            check_dependencies
            setup_environment
            setup_webhook
            create_action_workflow
            create_python_handler
            log_info "Setup completed successfully"
            log_info "To start polling, run: $0 poll"
            ;;
    esac
    
    log_info "GitHub Automator finished"
}

# Run main function
main "$@"