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
