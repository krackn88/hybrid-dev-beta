import logging
from provider_manager import ProviderManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PerformanceMetrics:
    def __init__(self):
        self.provider_manager = ProviderManager()

    def track_metrics(self, metrics):
        prompt = f"Track the following performance metrics: {metrics}"
        tracking_info = self.provider_manager.get_completions(prompt)
        self.provider_manager.handle_completions(tracking_info)
        return tracking_info

# Example usage
if __name__ == "__main__":
    metrics_tracker = PerformanceMetrics()
    performance_metrics = {
        "response_time": "200ms",
        "accuracy": "95%",
        "completion_rate": "90%"
    }
    tracking_info = metrics_tracker.track_metrics(performance_metrics)
    print(tracking_info)
