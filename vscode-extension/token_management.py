import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TokenManagement:
    def __init__(self):
        self.tokens = {}

    def add_token(self, service_name, token):
        self.tokens[service_name] = token

    def get_token(self, service_name):
        return self.tokens.get(service_name)

    def remove_token(self, service_name):
        if service_name in self.tokens:
            del self.tokens[service_name]

# Example usage
if __name__ == "__main__":
    token_manager = TokenManagement()
    token_manager.add_token("github", os.getenv("GITHUB_PAT"))
    token_manager.add_token("openai", os.getenv("OPENAI_API_KEY"))
    token_manager.add_token("anthropic", os.getenv("ANTHROPIC_API_KEY"))
    
    print(token_manager.get_token("github"))
    token_manager.remove_token("github")
