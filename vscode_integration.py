import os
import logging
from vscode import Vscode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VscodeIntegration:
    def __init__(self):
        self.vscode = Vscode()

    def open_file(self, file_path):
        try:
            self.vscode.open(file_path)
            logging.info(f"Opened file: {file_path}")
        except Exception as e:
            logging.error(f"Failed to open file: {e}")

    def add_sidebar_item(self, item_name, item_action):
        try:
            self.vscode.add_sidebar_item(item_name, item_action)
            logging.info(f"Added sidebar item: {item_name}")
        except Exception as e:
            logging.error(f"Failed to add sidebar item: {e}")

    def add_command_palette_item(self, item_name, item_action):
        try:
            self.vscode.add_command_palette_item(item_name, item_action)
            logging.info(f"Added command palette item: {item_name}")
        except Exception as e:
            logging.error(f"Failed to add command palette item: {e}")

    def update_status_bar(self, message, color):
        try:
            self.vscode.update_status_bar(message, color)
            logging.info(f"Updated status bar with message: {message}")
        except Exception as e:
            logging.error(f"Failed to update status bar: {e}")

    def add_editor_decoration(self, decoration_type, range_start, range_end, options):
        try:
            self.vscode.add_editor_decoration(decoration_type, range_start, range_end, options)
            logging.info(f"Added editor decoration: {decoration_type}")
        except Exception as e:
            logging.error(f"Failed to add editor decoration: {e}")

# Example usage
if __name__ == "__main__":
    vscode_integration = VscodeIntegration()
    
    # Open a file
    vscode_integration.open_file("example.py")
    
    # Add a sidebar item
    vscode_integration.add_sidebar_item("Run Tests", "run_tests")
    
    # Add a command palette item
    vscode_integration.add_command_palette_item("Build Project", "build_project")
    
    # Update the status bar
    vscode_integration.update_status_bar("Running...", "yellow")
    
    # Add an editor decoration
    vscode_integration.add_editor_decoration("highlight", (0, 0), (0, 10), {"backgroundColor": "rgba(255,0,0,0.3)"})
