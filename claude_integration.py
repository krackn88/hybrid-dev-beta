import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Anthropic API endpoint for Claude
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/claude"

# Function to trigger Claude completions
def get_claude_completions(prompt, user_token):
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "max_tokens": 150,
        "temperature": 0.7,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }
    response = requests.post(f"{ANTHROPIC_API_URL}/completions", headers=headers, json=data)
    if response.status_code == 200:
        logging.info("Claude completions retrieved successfully.")
        return response.json()
    else:
        logging.error(f"Failed to retrieve Claude completions: {response.status_code} {response.text}")
        return None

# Function to handle Claude completions
def handle_claude_completions(completions):
    if completions:
        for completion in completions.get('choices', []):
            logging.info(f"Completion: {completion['text']}")
    else:
        logging.error("No completions to handle.")

# Example usage
if __name__ == "__main__":
    user_token = os.getenv("ANTHROPIC_API_KEY")
    if not user_token:
        logging.error("Anthropic API Key is not set.")
    else:
        prompt = "def hello_world():"
        completions = get_claude_completions(prompt, user_token)
        handle_claude_completions(completions)
