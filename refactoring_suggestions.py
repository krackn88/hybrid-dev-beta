import logging
from provider_manager import ProviderManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RefactoringSuggestions:
    def __init__(self):
        self.provider_manager = ProviderManager()

    def suggest_refactoring(self, code):
        prompt = f"Suggest refactoring for the following code: {code}"
        suggestions = self.provider_manager.get_completions(prompt)
        self.provider_manager.handle_completions(suggestions)
        return suggestions

# Example usage
if __name__ == "__main__":
    refactoring_suggester = RefactoringSuggestions()
    code_snippet = """
def calculate_factorial(n):
    if n == 0:
        return 1
    else:
        return n * calculate_factorial(n-1)
"""
    suggestions = refactoring_suggester.suggest_refactoring(code_snippet)
    print(suggestions)
