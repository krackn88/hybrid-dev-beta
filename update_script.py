import os
from github import Github
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Error: {result.stderr}")
        raise Exception(f"Command failed: {command}")
    return result.stdout

# Authenticate using the personal access token
token = os.getenv('PAT')
g = Github(token)

repo_name = "krackn88/hybrid-dev-beta"
repo = g.get_repo(repo_name)

# Correct repository URLs
repo_urls = {
    "kracknai_badapple": "https://github.com/krackn88/kracknai_badapple.git",
    "anthropic-quickstarts": "https://github.com/anthropics/anthropic-quickstarts.git"
}

# Fetch new changes from both repos and merge
for repo_key, repo_url in repo_urls.items():
    logging.info(f"Pulling changes from {repo_key} repository...")
    try:
        run_command(f"git pull {repo_url} main")
    except Exception as e:
        logging.error(f"Failed to pull changes from {repo_url}: {e}")

# Merge changes and handle any conflicts
logging.info("Merging changes...")
try:
    run_command("git merge --no-edit")
except Exception as e:
    logging.error(f"Failed to merge changes: {e}")

# Commit and push the changes
logging.info("Pushing changes to the repository...")
try:
    run_command("git add .")
    run_command("git commit -m 'Automated update'")
    run_command("git push")
    logging.info("Update completed successfully.")
except Exception as e:
    logging.error(f"Failed to push changes: {e}")
