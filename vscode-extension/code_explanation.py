import logging
from provider_manager import ProviderManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CodeExplanation:
    def __init__(self):
        self.provider_manager = ProviderManager()

    def explain_code(self, code):
        prompt = f"Explain the following code: {code}"
        explanations = self.provider_manager.get_completions(prompt)
        self.provider_manager.handle_completions(explanations)
        return explanations

# Example usage
if __name__ == "__main__":
    code_explainer = CodeExplanation()
    code_snippet = """
def hello_world():
    print('Hello, world!')
"""
    explanations = code_explainer.explain_code(code_snippet)
    print(explanations)
