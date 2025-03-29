import logging
from provider_manager import ProviderManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FunctionGeneration:
    def __init__(self):
        self.provider_manager = ProviderManager()

    def generate_function(self, description):
        prompt = f"Generate a function based on the following description: {description}"
        completions = self.provider_manager.get_completions(prompt)
        self.provider_manager.handle_completions(completions)
        return completions

# Example usage
if __name__ == "__main__":
    function_gen = FunctionGeneration()
    description = "A function that calculates the factorial of a number."
    completions = function_gen.generate_function(description)
    print(completions)
