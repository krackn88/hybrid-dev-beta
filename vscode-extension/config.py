import os

class Config:
    def __init__(self):
        self.provider = os.getenv("DEFAULT_PROVIDER", "copilot")

    def set_provider(self, provider_name):
        self.provider = provider_name

    def get_provider(self):
        return self.provider

config = Config()
