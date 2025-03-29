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

# Fetch new changes from both repos and merge
logging.info("Pulling changes from kracknai_badapple repository...")
run_command("git pull https://github.com/krackn88/kracknai_badapple.git main")

logging.info("Pulling changes from anthropic-quickstarts repository...")
run_command("git pull https://github.com/anthropics/anthropic-quickstarts.git main")

# Merge changes and handle any conflicts
logging.info("Merging changes...")
run_command("git merge --no-edit")

# Commit and push the changes
logging.info("Pushing changes to the repository...")
run_command("git add .")
run_command("git commit -m 'Automated update'")
run_command("git push")
logging.info("Update completed successfully.")
