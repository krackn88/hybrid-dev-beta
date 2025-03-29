import os
import requests
import logging
from provider_interface import ProviderInterface
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# GitHub API endpoint for Copilot
GITHUB_API_URL = "https://api.github.com"

class CopilotProvider(ProviderInterface):
    def get_completions(self, prompt):
        headers = {
            "Authorization": f"token {self.user_token}",
            "Accept": "application/vnd.github.copilot-preview+json"
        }
        data = {
            "prompt": prompt,
            "max_tokens": 150,
            "temperature": 0.7,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }
        response = requests.post(f"{GITHUB_API_URL}/copilot", headers=headers, json=data)
        if response.status_code == 200:
            logging.info("Copilot completions retrieved successfully.")
            return response.json()
        else:
            logging.error(f"Failed to retrieve Copilot completions: {response.status_code} {response.text}")
            return None

    def handle_completions(self, completions):
        if completions:
            for completion in completions.get('choices', []):
                logging.info(f"Completion: {completion['text']}")
        else:
            logging.error("No completions to handle.")

# Example usage
if __name__ == "__main__":
    user_token = os.getenv("GITHUB_PAT")
    if not user_token:
        logging.error("GitHub Personal Access Token (PAT) is not set.")
    else:
        prompt = "def hello_world():"
        copilot_provider = CopilotProvider(user_token)
        completions = copilot_provider.get_completions(prompt)
        copilot_provider.handle_completions(completions)
