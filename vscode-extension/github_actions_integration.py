import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GitHubActionsIntegration:
    def __init__(self, repo_name, owner_name):
        self.repo_name = repo_name
        self.owner_name = owner_name
        self.token = os.getenv("GITHUB_PAT")
        self.base_url = f"https://api.github.com/repos/{owner_name}/{repo_name}"

    def get_headers(self):
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def list_workflows(self):
        url = f"{self.base_url}/actions/workflows"
        response = requests.get(url, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to list workflows: {response.status_code} {response.text}")
            return None

    def trigger_workflow(self, workflow_id, ref="main"):
        url = f"{self.base_url}/actions/workflows/{workflow_id}/dispatches"
        data = {
            "ref": ref
        }
        response = requests.post(url, headers=self.get_headers(), json=data)
        if response.status_code == 204:
            logging.info("Workflow triggered successfully.")
        else:
            logging.error(f"Failed to trigger workflow: {response.status_code} {response.text}")

    def get_workflow_run_status(self, run_id):
        url = f"{self.base_url}/actions/runs/{run_id}"
        response = requests.get(url, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to get workflow run status: {response.status_code} {response.text}")
            return None

# Example usage
if __name__ == "__main__":
    repo_name = "hybrid-dev-beta"
    owner_name = "krackn88"
    gha_integration = GitHubActionsIntegration(repo_name, owner_name)
    
    # List workflows
    workflows = gha_integration.list_workflows()
    print(workflows)
    
    # Trigger a workflow (use a valid workflow_id from the listed workflows)
    workflow_id = "example_workflow_id"
    gha_integration.trigger_workflow(workflow_id)
    
    # Get workflow run status (use a valid run_id)
    run_id = "example_run_id"
    status = gha_integration.get_workflow_run_status(run_id)
    print(status)
