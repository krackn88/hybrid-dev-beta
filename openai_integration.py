import os
import openai
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# OpenAI API endpoint
OPENAI_API_URL = "https://api.openai.com/v1/engines/davinci-codex/completions"

# Function to trigger OpenAI completions
def get_openai_completions(prompt, user_token):
    openai.api_key = user_token
    try:
        response = openai.Completion.create(
            engine="davinci-codex",
            prompt=prompt,
            max_tokens=150,
            temperature=0.7,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        logging.info("OpenAI completions retrieved successfully.")
        return response
    except Exception as e:
        logging.error(f"Failed to retrieve OpenAI completions: {e}")
        return None

# Function to handle OpenAI completions
def handle_openai_completions(completions):
    if completions:
        for choice in completions.choices:
            logging.info(f"Completion: {choice.text}")
    else:
        logging.error("No completions to handle.")

# Example usage
if __name__ == "__main__":
    user_token = os.getenv("OPENAI_API_KEY")
    if not user_token:
        logging.error("OpenAI API Key is not set.")
    else:
        prompt = "def hello_world():"
        completions = get_openai_completions(prompt, user_token)
        handle_openai_completions(completions)
