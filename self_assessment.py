import logging
from provider_manager import ProviderManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SelfAssessment:
    def __init__(self):
        self.provider_manager = ProviderManager()

    def assess_performance(self, metrics):
        prompt = f"Assess the following performance metrics: {metrics}"
        assessment = self.provider_manager.get_completions(prompt)
        self.provider_manager.handle_completions(assessment)
        return assessment

# Example usage
if __name__ == "__main__":
    self_assessor = SelfAssessment()
    performance_metrics = {
        "response_time": "200ms",
        "accuracy": "95%",
        "completion_rate": "90%"
    }
    assessment = self_assessor.assess_performance(performance_metrics)
    print(assessment)
