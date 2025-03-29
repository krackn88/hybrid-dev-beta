import logging
from provider_manager import ProviderManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SemanticCodeSearch:
    def __init__(self):
        self.provider_manager = ProviderManager()

    def search_code(self, query):
        results = self.provider_manager.get_completions(query)
        self.provider_manager.handle_completions(results)
        return results

# Example usage
if __name__ == "__main__":
    semantic_search = SemanticCodeSearch()
    query = "How does authentication work in this repo?"
    results = semantic_search.search_code(query)
    print(results)
