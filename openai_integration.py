import os
import openai
import logging
from provider_interface import ProviderInterface
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levellevel)s - %(message)s')

# OpenAI API endpoint
OPENAI_API_URL = "https://api.openai.com/v1/engines/davinci-codex/completions"

class OpenAIProvider(ProviderInterface):
    def get_completions(self, prompt):
        openai.api_key = self.user_token
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

    def handle_completions(self, completions):
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
        openai_provider = OpenAIProvider(user_token)
        completions = openai_provider.get_completions(prompt)
        openai_provider.handle_completions(completions)
