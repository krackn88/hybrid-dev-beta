import logging
from provider_manager import ProviderManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CodeCompletion:
    def __init__(self):
        self.provider_manager = ProviderManager()

    def complete_code(self, prompt):
        completions = self.provider_manager.get_completions(prompt)
        self.provider_manager.handle_completions(completions)
        return completions

# Example usage
if __name__ == "__main__":
    code_completion = CodeCompletion()
    prompt = "def hello_world():"
    completions = code_completion.complete_code(prompt)
    print(completions)
