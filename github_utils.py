#!/usr/bin/env python3
"""
GitHub Utilities - Python companion for github_automator.sh

This module provides advanced GitHub automation capabilities using the PyGitHub library,
offering more complex functionality than what's possible in bash scripts alone.

Usage:
    python github_utils.py [command] [args]

Commands:
    analyze_repo     - Generate repository statistics and insights
    monitor          - Start real-time monitoring with advanced event handling
    backup           - Back up repository content and metadata
    auto_label       - Set up and manage automatic issue/PR labeling
    security_scan    - Scan repository for security issues

Author: krackn88
Date: 2025-03-29
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

try:
    from github import Github, GithubException, Repository, Issue, PullRequest, Commit
    import requests
    import yaml
except ImportError:
    print("Required packages not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyGithub", "requests", "pyyaml"])
    from github import Github, GithubException, Repository, Issue, PullRequest, Commit
    import requests
    import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("github_utils.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("github-utils")

class GitHubUtils:
    """Main class for GitHub repository utilities and automation."""
    
    def __init__(self, token: Optional[str] = None, repo_name: Optional[str] = None):
        """
        Initialize the GitHub utilities with authentication and repository info.
        
        Args:
            token: GitHub personal access token (optional, will check env vars if None)
            repo_name: Repository name in format "owner/repo" (optional, will check env vars if None)
        """
        # Get token from params, env vars, or GitHub CLI
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not self.token:
            try:
                import subprocess
                self.token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
            except Exception as e:
                logger.error(f"Failed to get GitHub token from GitHub CLI: {e}")
                
        if not self.token:
            raise ValueError("No GitHub token provided. Set GITHUB_TOKEN environment variable or provide token parameter.")
        
        # Initialize GitHub client
        self.github = Github(self.token)
        
        # Get repository info
        self.repo_name = repo_name or os.environ.get("GITHUB_REPOSITORY")
        if not self.repo_name and os.path.exists(".git"):
            try:
                import subprocess
                remote_url = subprocess.check_output(
                    ["git", "config", "--get", "remote.origin.url"], 
                    text=True
                ).strip()
                # Extract repo name from URL
                if "github.com" in remote_url:
                    if remote_url.startswith("https://"):
                        self.repo_name = remote_url.split("github.com/")[1].rstrip(".git")
                    elif remote_url.startswith("git@"):
                        self.repo_name = remote_url.split("github.com:")[1].rstrip(".git")
            except Exception as e:
                logger.warning(f"Failed to get repository name from git config: {e}")
        
        if not self.repo_name:
            raise ValueError("Repository name not provided. Set GITHUB_REPOSITORY environment variable or provide repo_name parameter.")
        
        # Initialize repository object
        self.repo = self.github.get_repo(self.repo_name)
        logger.info(f"Initialized GitHub utils for repository: {self.repo_name}")
        
        # Set up rate limit handling
        self.remaining_rate_limit = self.github.get_rate_limit().core.remaining
        logger.info(f"Current rate limit remaining: {self.remaining_rate_limit}")
    
    def _check_rate_limit(self) -> None:
        """Check and handle GitHub API rate limit."""
        rate_limit = self.github.get_rate_limit()
        self.remaining_rate_limit = rate_limit.core.remaining
        
        if self.remaining_rate_limit < 100:
            reset_time = rate_limit.core.reset
            current_time = datetime.utcnow()
            sleep_time = (reset_time - current_time).total_seconds()
            
            if sleep_time > 0:
                logger.warning(f"Rate limit low ({self.remaining_rate_limit}), sleeping for {sleep_time} seconds until reset")
                time.sleep(min(sleep_time + 5, 3600))  # Sleep until reset, max 1 hour
                self.remaining_rate_limit = self.github.get_rate_limit().core.remaining
                logger.info(f"Rate limit refreshed. New remaining: {self.remaining_rate_limit}")
    
    def analyze_repository(self) -> Dict[str, Any]:
        """
        Analyze repository and generate statistics and insights.
        
        Returns:
            Dict containing repository analysis data
        """
        logger.info(f"Analyzing repository: {self.repo_name}")
        self._check_rate_limit()
        
        # Get basic repository info
        analysis = {
            "name": self.repo.name,
            "owner": self.repo.owner.login,
            "description": self.repo.description,
            "created_at": self.repo.created_at.isoformat(),
            "updated_at": self.repo.updated_at.isoformat(),
            "language": self.repo.language,
            "stars": self.repo.stargazers_count,
            "forks": self.repo.forks_count,
            "watchers": self.repo.watchers_count,
            "open_issues": self.repo.open_issues_count,
            "topics": self.repo.get_topics(),
            "license": self.repo.license.name if self.repo.license else None,
            "is_template": self.repo.is_template,
        }
        
        # Get commit statistics (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        commits = list(self.repo.get_commits(since=thirty_days_ago))
        
        analysis["commit_stats"] = {
            "total_last_30_days": len(commits),
            "authors": self._count_unique_authors(commits),
            "top_files_changed": self._get_top_files_changed(commits[:50])  # Limit to 50 most recent
        }
        
        # Get PR statistics
        open_prs = list(self.repo.get_pulls(state="open"))
        closed_prs = list(self.repo.get_pulls(state="closed")[:100])  # Last 100 closed PRs
        
        analysis["pr_stats"] = {
            "open": len(open_prs),
            "avg_time_to_merge": self._calculate_avg_time_to_merge(closed_prs),
            "avg_comments_per_pr": self._calculate_avg_comments(open_prs + closed_prs[:20]),
        }
        
        # Get issue statistics
        open_issues = list(self.repo.get_issues(state="open"))
        
        analysis["issue_stats"] = {
            "open": len(open_issues),
            "avg_age_days": self._calculate_avg_issue_age(open_issues),
            "top_labels": self._get_top_labels(open_issues),
        }
        
        # Get branch info
        analysis["branches"] = {
            "count": len(list(self.repo.get_branches())),
            "default": self.repo.default_branch,
            "protected": [b.name for b in self.repo.get_branches() if b.protected],
        }
        
        logger.info(f"Repository analysis complete for {self.repo_name}")
        return analysis
    
    def _count_unique_authors(self, commits: List[Commit.Commit]) -> Dict[str, int]:
        """Count commits by unique authors."""
        authors = {}
        for commit in commits:
            author = commit.commit.author.name
            authors[author] = authors.get(author, 0) + 1
        return dict(sorted(authors.items(), key=lambda x: x[1], reverse=True))
    
    def _get_top_files_changed(self, commits: List[Commit.Commit]) -> Dict[str, int]:
        """Get most frequently changed files from commits."""
        files_changed = {}
        for commit in commits:
            try:
                for file in commit.files:
                    files_changed[file.filename] = files_changed.get(file.filename, 0) + 1
            except GithubException:
                # Some commit data might not be accessible
                continue
        
        # Return top 10 most changed files
        return dict(sorted(files_changed.items(), key=lambda x: x[1], reverse=True)[:10])
    
    def _calculate_avg_time_to_merge(self, prs: List[PullRequest.PullRequest]) -> float:
        """Calculate average time to merge for closed PRs."""
        merge_times = []
        for pr in prs:
            if pr.merged and pr.created_at and pr.merged_at:
                merge_time = (pr.merged_at - pr.created_at).total_seconds() / 3600  # hours
                merge_times.append(merge_time)
        
        return sum(merge_times) / len(merge_times) if merge_times else 0
    
    def _calculate_avg_comments(self, items: List[Union[Issue.Issue, PullRequest.PullRequest]]) -> float:
        """Calculate average comments per issue or PR."""
        comment_counts = []
        for item in items:
            try:
                comment_counts.append(item.comments)
            except GithubException:
                continue
                
        return sum(comment_counts) / len(comment_counts) if comment_counts else 0
    
    def _calculate_avg_issue_age(self, issues: List[Issue.Issue]) -> float:
        """Calculate average age of open issues in days."""
        now = datetime.utcnow()
        ages = [(now - issue.created_at).total_seconds() / 86400 for issue in issues]  # days
        return sum(ages) / len(ages) if ages else 0
    
    def _get_top_labels(self, issues: List[Issue.Issue]) -> Dict[str, int]:
        """Get most frequent labels from issues."""
        labels = {}
        for issue in issues:
            for label in issue.labels:
                labels[label.name] = labels.get(label.name, 0) + 1
        
        # Return top 10 most frequent labels
        return dict(sorted(labels.items(), key=lambda x: x[1], reverse=True)[:10])
    
    def monitor_repository(self, interval: int = 60, callback: Optional[callable] = None) -> None:
        """
        Start real-time monitoring of repository events.
        
        Args:
            interval: Polling interval in seconds
            callback: Optional callback function to be called with events
        """
        logger.info(f"Starting repository monitoring for {self.repo_name} with {interval}s interval")
        
        last_commit_sha = None
        last_pr_number = None
        last_issue_number = None
        
        try:
            while True:
                self._check_rate_limit()
                
                # Check for new commits
                latest_commit = next(self.repo.get_commits(), None)
                if latest_commit and latest_commit.sha != last_commit_sha:
                    if last_commit_sha is not None:  # Skip first run
                        new_commits = []
                        for commit in self.repo.get_commits():
                            if commit.sha == last_commit_sha:
                                break
                            new_commits.append(commit)
                        
                        if new_commits:
                            logger.info(f"Found {len(new_commits)} new commits")
                            if callback:
                                callback("commits", new_commits)
                    
                    last_commit_sha = latest_commit.sha
                
                # Check for new PRs
                open_prs = list(self.repo.get_pulls(state="open", sort="created", direction="desc")[:5])
                if open_prs and (last_pr_number is None or open_prs[0].number != last_pr_number):
                    if last_pr_number is not None:  # Skip first run
                        new_prs = [pr for pr in open_prs if pr.number > last_pr_number]
                        if new_prs:
                            logger.info(f"Found {len(new_prs)} new pull requests")
                            if callback:
                                callback("pull_requests", new_prs)
                    
                    last_pr_number = open_prs[0].number if open_prs else None
                
                # Check for new issues
                open_issues = list(self.repo.get_issues(state="open", sort="created", direction="desc")[:5])
                # Filter out PRs that show up as issues
                open_issues = [i for i in open_issues if not hasattr(i, 'pull_request') or i.pull_request is None]
                
                if open_issues and (last_issue_number is None or open_issues[0].number != last_issue_number):
                    if last_issue_number is not None:  # Skip first run
                        new_issues = [issue for issue in open_issues if issue.number > last_issue_number]
                        if new_issues:
                            logger.info(f"Found {len(new_issues)} new issues")
                            if callback:
                                callback("issues", new_issues)
                    
                    last_issue_number = open_issues[0].number if open_issues else None
                
                logger.debug(f"Monitoring cycle complete, sleeping for {interval} seconds")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error during monitoring: {e}")
            raise
    
    def create_auto_labeler(self, config_file: str = "auto_labels.yml") -> None:
        """
        Create configuration for automatic issue and PR labeling.
        
        Args:
            config_file: Path to configuration file
        """
        if os.path.exists(config_file):
            logger.warning(f"Config file {config_file} already exists. Will not overwrite.")
            return
        
        # Create default configuration
        default_config = {
            "version": "1.0",
            "settings": {
                "ignore_bots": True,
                "process_existing": False,
                "add_comments": True
            },
            "label_rules": {
                "issues": [
                    {
                        "label": "bug",
                        "keywords": ["bug", "crash", "error", "exception", "fails", "broken"],
                        "title_match": True,
                        "body_match": True
                    },
                    {
                        "label": "enhancement",
                        "keywords": ["feature", "enhancement", "improve", "request"],
                        "title_match": True,
                        "body_match": True
                    },
                    {
                        "label": "question",
                        "keywords": ["question", "help", "how to", "?"],
                        "title_match": True,
                        "body_match": False
                    },
                    {
                        "label": "documentation",
                        "keywords": ["docs", "documentation", "readme", "typo"],
                        "title_match": True,
                        "body_match": True
                    }
                ],
                "pull_requests": [
                    {
                        "label": "dependencies",
                        "file_patterns": ["package.json", "requirements.txt", "go.mod", "*.lock"],
                        "max_files": 3
                    },
                    {
                        "label": "frontend",
                        "file_patterns": ["*.js", "*.ts", "*.jsx", "*.tsx", "*.css", "*.scss", "*.html"],
                        "min_files_ratio": 0.7
                    },
                    {
                        "label": "backend",
                        "file_patterns": ["*.py", "*.go", "*.java", "*.rb", "*.php"],
                        "min_files_ratio": 0.7
                    },
                    {
                        "label": "tests",
                        "file_patterns": ["test_*.py", "*_test.go", "*.spec.js", "*.test.js"],
                        "min_files_ratio": 0.5
                    },
                    {
                        "label": "small-change",
                        "total_changes": {"max": 50}
                    },
                    {
                        "label": "large-change",
                        "total_changes": {"min": 500}
                    }
                ]
            }
        }
        
        # Write configuration to file
        with open(config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Created auto-labeler configuration at {config_file}")
        
        # Create GitHub Action workflow file for auto-labeling
        os.makedirs(".github/workflows", exist_ok=True)
        
        workflow = {
            "name": "Auto Label",
            "on": {
                "issues": {"types": ["opened", "edited"]},
                "pull_request": {"types": ["opened", "synchronize"]}
            },
            "jobs": {
                "auto-label": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v3"},
                        {
                            "name": "Set up Python",
                            "uses": "actions/setup-python@v4",
                            "with": {"python-version": "3.10"}
                        },
                        {
                            "name": "Install dependencies",
                            "run": "pip install PyGithub pyyaml"
                        },
                        {
                            "name": "Run auto-labeler",
                            "run": "python github_utils.py auto_label --run",
                            "env": {"GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}
                        }
                    ]
                }
            }
        }
        
        with open(".github/workflows/auto-label.yml", 'w') as f:
            yaml.dump(workflow, f, default_flow_style=False, sort_keys=False)
        
        logger.info("Created GitHub Action workflow for auto-labeling at .github/workflows/auto-label.yml")
    
    def run_auto_labeler(self, config_file: str = "auto_labels.yml") -> None:
        """
        Run the auto-labeler for issues and PRs.
        
        Args:
            config_file: Path to configuration file
        """
        if not os.path.exists(config_file):
            logger.error(f"Config file {config_file} not found")
            return
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("Running auto-labeler")
        
        # Determine what to process based on GitHub event
        event_name = os.environ.get("GITHUB_EVENT_NAME")
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        
        if event_path and os.path.exists(event_path):
            with open(event_path, 'r') as f:
                event_data = json.load(f)
                
            if event_name == "issues" and "issue" in event_data:
                issue_number = event_data["issue"]["number"]
                self._process_issue_labels(issue_number, config["label_rules"]["issues"])
                
            elif event_name == "pull_request" and "pull_request" in event_data:
                pr_number = event_data["pull_request"]["number"]
                self._process_pr_labels(pr_number, config["label_rules"]["pull_requests"])
        
        # If not running in GitHub Actions or processing existing items
        elif config["settings"].get("process_existing", False):
            # Process open issues
            for issue in self.repo.get_issues(state="open"):
                if not hasattr(issue, 'pull_request') or issue.pull_request is None:
                    self._process_issue_labels(issue.number, config["label_rules"]["issues"])
            
            # Process open PRs
            for pr in self.repo.get_pulls(state="open"):
                self._process_pr_labels(pr.number, config["label_rules"]["pull_requests"])
    
    def _process_issue_labels(self, issue_number: int, rules: List[Dict]) -> None:
        """Process labeling rules for an issue."""
        issue = self.repo.get_issue(issue_number)
        
        # Skip bot issues if configured
        if issue.user.type == "Bot" and self.config["settings"].get("ignore_bots", True):
            return
        
        applied_labels = []
        for rule in rules:
            label = rule["label"]
            keywords = rule.get("keywords", [])
            
            matches = False
            if rule.get("title_match", False) and any(k.lower() in issue.title.lower() for k in keywords):
                matches = True
            
            if not matches and rule.get("body_match", False) and issue.body and any(k.lower() in issue.body.lower() for k in keywords):
                matches = True
            
            if matches and label not in [l.name for l in issue.labels]:
                issue.add_to_labels(label)
                applied_labels.append(label)
                logger.info(f"Applied label '{label}' to issue #{issue_number}")
        
        # Add comment if configured
        if applied_labels and self.config["settings"].get("add_comments", False):
            comment = f"Applied labels: {', '.join(['`' + l + '`' for l in applied_labels])}"
            issue.create_comment(comment)
    
    def _process_pr_labels(self, pr_number: int, rules: List[Dict]) -> None:
        """Process labeling rules for a pull request."""
        pr = self.repo.get_pull(pr_number)
        
        # Skip bot PRs if configured
        if pr.user.type == "Bot" and self.config["settings"].get("ignore_bots", True):
            return
        
        # Get files changed in PR
        files = list(pr.get_files())
        total_changes = sum(f.changes for f in files)
        filenames = [f.filename for f in files]
        
        applied_labels = []
        for rule in rules:
            label = rule["label"]
            matches = False
            
            # Check file patterns
            if "file_patterns" in rule:
                matching_files = 0
                patterns = rule["file_patterns"]
                
                import fnmatch
                for pattern in patterns:
                    for filename in filenames:
                        if fnmatch.fnmatch(filename, pattern):
                            matching_files += 1
                
                # Check if enough files match the patterns
                if "max_files" in rule and matching_files <= rule["max_files"]:
                    matches = True
                
                if "min_files_ratio" in rule and matching_files / len(filenames) >= rule["min_files_ratio"]:
                    matches = True
            
            # Check total changes
            if "total_changes" in rule:
                criteria = rule["total_changes"]
                if "max" in criteria and total_changes <= criteria["max"]:
                    matches = True
                if "min" in criteria and total_changes >= criteria["min"]:
                    matches = True
            
            if matches and label not in [l.name for l in pr.labels]:
                pr.add_to_labels(label)
                applied_labels.append(label)
                logger.info(f"Applied label '{label}' to PR #{pr_number}")
        
        # Add comment if configured
        if applied_labels and self.config["settings"].get("add_comments", False):
            comment = f"Applied labels: {', '.join(['`' + l + '`' for l in applied_labels])}"
            pr.create_comment(comment)
    
    def backup_repository(self, output_dir: str = "backup") -> str:
        """
        Create a backup of repository content and metadata.
        
        Args:
            output_dir: Directory to store backup
            
        Returns:
            Path to backup directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(output_dir, f"{self.repo.name}_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)
        
        logger.info(f"Creating repository backup at {backup_dir}")
        
        # Save repository metadata
        repo_info = {
            "name": self.repo.name,
            "full_name": self.repo.full_name,
            "description": self.repo.description,
            "created_at": self.repo.created_at.isoformat(),
            "updated_at": self.repo.updated_at.isoformat(),
            "pushed_at": self.repo.pushed_at.isoformat(),
            "homepage": self.repo.homepage,
            "language": self.repo.language,
            "forks_count": self.repo.forks_count,
            "stargazers_count": self.repo.stargazers_count,
            "watchers_count": self.repo.watchers_count,
            "size": self.repo.size,
            "default_branch": self.repo.default_branch,
            "topics": self.repo.get_topics(),
            "has_wiki": self.repo.has_wiki,
            "has_pages": self.repo.has_pages,
            "has_projects": self.repo.has_projects,
            "has_downloads": self.repo.has_downloads,
            "archived": self.repo.archived,
            "visibility": self.repo.visibility,
        }
        
        with open(os.path.join(backup_dir, "repository_info.json"), 'w') as f:
            json.dump(repo_info, f, indent=2)
        
        # Save branches
        branches = []
        for branch in self.repo.get_branches():
            branches.append({
                "name": branch.name,
                "protected": branch.protected,
                "sha": branch.commit.sha
            })
        
        with open(os.path.join(backup_dir, "branches.json"), 'w') as f:
            json.dump(branches, f, indent=2)
        
        # Save recent commits
        commits = []
        for commit in self.repo.get_commits()[:100]:  # Last 100 commits
            commits.append({
                "sha": commit.sha,
                "message": commit.commit.message,
                "author": commit.commit.author.name,
                "email": commit.commit.author.email,
                "date": commit.commit.author.date.isoformat(),
                "url": commit.html_url
            })
        
        with open(os.path.join(backup_dir, "recent_commits.json"), 'w') as f:
            json.dump(commits, f, indent=2)
        
        # Save issues
        issues_dir = os.path.join(backup_dir, "issues")
        os.makedirs(issues_dir, exist_ok=True)
        
        for issue in self.repo.get_issues(state="all")[:200]:  # Last 200 issues
            issue_data = {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat(),
                "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
                "labels": [l.name for l in issue.labels],
                "user": issue.user.login,
                "assignees": [a.login for a in issue.assignees],
                "is_pull_request": hasattr(issue, 'pull_request') and issue.pull_request is not None,
                "comments": []
            }
            
            # Add comments
            for comment in issue.get_comments():
                issue_data["comments"].append({
                    "user": comment.user.login,
                    "body": comment.body,
                    "created_at": comment.created_at.isoformat(),
                    "updated_at": comment.updated_at.isoformat()
                })
            
            with open(os.path.join(issues_dir, f"issue_{issue.number}.json"), 'w') as f:
                json.dump(issue_data, f, indent=2)
        
        # Save pull requests
        prs_dir = os.path.join(backup_dir, "pull_requests")
        os.makedirs(prs_dir, exist_ok=True)
        
        for pr in self.repo.get_pulls(state="all")[:100]:  # Last 100 PRs
            pr_data = {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "merged": pr.merged,
                "mergeable": pr.mergeable,
                "labels": [l.name for l in pr.labels],
                "user": pr.user.login,
                "assignees": [a.login for a in pr.assignees],
                "requested_reviewers": [r.login for r in pr.requested_reviewers],
                "head": {
                    "ref": pr.head.ref,
                    "sha": pr.head.sha,
                    "label": pr.head.label
                },
                "base": {
                    "ref": pr.base.ref,
                    "sha": pr.base.sha,
                    "label": pr.base.label
                },
                "comments": []
            }
            
            # Add comments
            for comment in pr.get_issue_comments():
                pr_data["comments"].append({
                    "user": comment.user.login,
                    "body": comment.body,
                    "created_at": comment.created_at.isoformat(),
                    "updated_at": comment.updated_at.isoformat()
                })
            
            with open(os.path.join(prs_dir, f"pr_{pr.number}.json"), 'w') as f:
                json.dump(pr_data, f, indent=2)
        
        # Save releases
        releases = []
        for release in self.repo.get_releases():
            releases.append({
                "id": release.id,
                "tag_name": release.tag_name,
                "name": release.title,
                "body": release.body,
                "draft": release.draft,
                "prerelease": release.prerelease,
                "created_at": release.created_at.isoformat(),
                "published_at": release.published_at.isoformat() if release.published_at else None,
                "author": release.author.login,
                "assets": [{
                    "name": asset.name,
                    "size": asset.size,
                    "download_count": asset.download_count,
                    "created_at": asset.created_at.isoformat(),
                    "updated_at": asset.updated_at.isoformat(),
                    "url": asset.browser_download_url
                } for asset in release.get_assets()]
            })
        
        with open(os.path.join(backup_dir, "releases.json"), 'w') as f:
            json.dump(releases, f, indent=2)
        
        # Save workflows
        try:
            workflows_dir = os.path.join(backup_dir, "workflows")
            os.makedirs(workflows_dir, exist_ok=True)
            
            workflows = self.repo.get_workflows()
            for workflow in workflows:
                workflow_data = {
                    "id": workflow.id,
                    "name": workflow.name,
                    "path": workflow.path,
                    "state": workflow.state,
                    "created_at": workflow.created_at.isoformat(),
                    "updated_at": workflow.updated_at.isoformat(),
                    "runs": []
                }
                
                # Get recent workflow runs
                for run in workflow.get_runs()[:20]:  # Last 20 runs
                    workflow_data["runs"].append({
                        "id": run.id,
                        "name": run.name,
                        "status": run.status,
                        "conclusion": run.conclusion,
                        "created_at": run.created_at.isoformat(),
                        "updated_at": run.updated_at.isoformat()
                    })
                
                with open(os.path.join(workflows_dir, f"workflow_{workflow.id}.json"), 'w') as f:
                    json.dump(workflow_data, f, indent=2)
        except GithubException:
            logger.warning("Could not retrieve workflow information, possibly lack of permissions")
        
        # Clone repository (optional - can be large)
        try:
            import subprocess
            source_dir = os.path.join(backup_dir, "source")
            os.makedirs(source_dir, exist_ok=True)
            
            logger.info(f"Cloning repository source to {source_dir}")
            subprocess.check_call(
                ["git", "clone", f"https://x-access-token:{self.token}@github.com/{self.repo_name}.git", source_dir],
                stderr=subprocess.PIPE  # Hide token from output
            )
        except Exception as e:
            logger.warning(f"Failed to clone repository source: {e}")
        
        logger.info(f"Repository backup completed at {backup_dir}")
        return backup_dir