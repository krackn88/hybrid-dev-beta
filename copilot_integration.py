import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# GitHub API endpoint for Copilot
GITHUB_API_URL = "https://api.github.com"

# Function to trigger Copilot completions
def get_copilot_completions(prompt, user_token):
    headers = {
        "Authorization": f"token {user_token}",
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

# Function to handle Copilot completions
def handle_copilot_completions(completions):
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
        completions = get_copilot_completions(prompt, user_token)
        handle_copilot_completions(completions)
