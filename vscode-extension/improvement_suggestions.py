import logging
from provider_manager import ProviderManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImprovementSuggestions:
    def __init__(self):
        self.provider_manager = ProviderManager()

    def suggest_improvements(self, metrics):
        prompt = f"Suggest improvements based on the following performance metrics: {metrics}"
        suggestions = self.provider_manager.get_completions(prompt)
        self.provider_manager.handle_completions(suggestions)
        return suggestions

# Example usage
if __name__ == "__main__":
    suggester = ImprovementSuggestions()
    performance_metrics = {
        "response_time": "200ms",
        "accuracy": "95%",
        "completion_rate": "90%"
    }
    suggestions = suggester.suggest_improvements(performance_metrics)
    print(suggestions)
