import os
from cryptography.fernet import Fernet
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SecureStorage:
    def __init__(self, key=None):
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data):
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data):
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# Example usage
if __name__ == "__main__":
    storage = SecureStorage()
    encrypted = storage.encrypt("my_secret_data")
    print("Encrypted:", encrypted)
    decrypted = storage.decrypt(encrypted)
    print("Decrypted:", decrypted)
