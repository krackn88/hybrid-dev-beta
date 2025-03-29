import logging
from provider_manager import ProviderManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UserApprovedLearning:
    def __init__(self):
        self.provider_manager = ProviderManager()

    def learn_from_interactions(self, interactions):
        prompt = f"Learn from the following interactions with user approval: {interactions}"
        learning_outcomes = self.provider_manager.get_completions(prompt)
        self.provider_manager.handle_completions(learning_outcomes)
        return learning_outcomes

# Example usage
if __name__ == "__main__":
    learner = UserApprovedLearning()
    interactions = [
        {"interaction": "Helped user with API request", "feedback": "positive"},
        {"interaction": "Suggested code refactor", "feedback": "negative"}
    ]
    learning_outcomes = learner.learn_from_interactions(interactions)
    print(learning_outcomes)
