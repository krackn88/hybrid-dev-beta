import logging

class ProviderInterface:
    def __init__(self, user_token):
        self.user_token = user_token

    def get_completions(self, prompt):
        raise NotImplementedError("This method should be overridden by subclasses")

    def handle_completions(self, completions):
        raise NotImplementedError("This method should be overridden by subclasses")
