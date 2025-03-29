from config import config
from copilot_integration import CopilotProvider
from claude_integration import ClaudeProvider
from openai_integration import OpenAIProvider

class ProviderManager:
    def __init__(self):
        self.providers = {
            "copilot": CopilotProvider,
            "claude": ClaudeProvider,
            "openai": OpenAIProvider
        }
        self.current_provider = self.get_provider_instance(config.get_provider())

    def get_provider_instance(self, provider_name):
        provider_class = self.providers.get(provider_name)
        if provider_class:
            return provider_class(self.get_token(provider_name))
        else:
            raise ValueError(f"Provider {provider_name} not supported")

    def get_token(self, provider_name):
        token_env_vars = {
            "copilot": "GITHUB_PAT",
            "claude": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY"
        }
        return os.getenv(token_env_vars[provider_name])

    def switch_provider(self, provider_name):
        config.set_provider(provider_name)
        self.current_provider = self.get_provider_instance(provider_name)

    def get_completions(self, prompt):
        return self.current_provider.get_completions(prompt)

    def handle_completions(self, completions):
        self.current_provider.handle_completions(completions)

# Example usage
if __name__ == "__main__":
    manager = ProviderManager()
    prompt = "def hello_world():"
    completions = manager.get_completions(prompt)
    manager.handle_completions(completions)
