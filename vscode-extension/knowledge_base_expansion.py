import logging
from provider_manager import ProviderManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class KnowledgeBaseExpansion:
    def __init__(self):
        self.provider_manager = ProviderManager()

    def expand_knowledge_base(self, new_knowledge):
        prompt = f"Expand the knowledge base with the following information: {new_knowledge}"
        expansion_info = self.provider_manager.get_completions(prompt)
        self.provider_manager.handle_completions(expansion_info)
        return expansion_info

# Example usage
if __name__ == "__main__":
    knowledge_expander = KnowledgeBaseExpansion()
    new_knowledge = "Information about the latest AI model updates."
    expansion_info = knowledge_expander.expand_knowledge_base(new_knowledge)
    print(expansion_info)
