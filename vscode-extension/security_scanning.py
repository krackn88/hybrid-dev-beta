import os
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SecurityScanning:
    def __init__(self, repo_path):
        self.repo_path = repo_path

    def run_scan(self):
        try:
            result = subprocess.run(["trufflehog", self.repo_path], capture_output=True, text=True)
            logging.info("Security scan completed successfully.")
            return result.stdout
        except Exception as e:
            logging.error(f"Failed to run security scan: {e}")
            return None

# Example usage
if __name__ == "__main__":
    scanner = SecurityScanning("/path/to/repo")
    scan_results = scanner.run_scan()
    print(scan_results)
