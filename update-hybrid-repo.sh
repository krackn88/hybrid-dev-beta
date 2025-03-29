#!/bin/bash

# ========================================================================
# Hybrid Dev Beta Repository Update Script
# Author: krackn88
# Version: 1.0.0
# ========================================================================

# Color definitions for better output readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration variables
REPO_NAME="hybrid-dev-beta"
REPO_OWNER="krackn88"
EXTENSION_DIR="vscode-extension"
EXTENSION_NAME="vscode-hybrid-extension"
LOG_FILE="hybrid_repo_update.log"
TODO_FILE="todo.md"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

# ========================================================================
# Utility Functions
# ========================================================================

log() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${timestamp} - $1" | tee -a "$LOG_FILE"
}

log_success() {
    log "${GREEN}SUCCESS: $1${NC}"
}

log_info() {
    log "${BLUE}INFO: $1${NC}"
}

log_warning() {
    log "${YELLOW}WARNING: $1${NC}"
}

log_error() {
    log "${RED}ERROR: $1${NC}"
}

# Error handler function
handle_error() {
    local exit_code=$?
    local line_number=$1
    
    if [ $exit_code -ne 0 ]; then
        log_error "Failed at line $line_number with exit code $exit_code"
        
        # Create backup of current state
        mkdir -p "$BACKUP_DIR"
        log_info "Creating backup at $BACKUP_DIR"
        cp -r ./* "$BACKUP_DIR/"
        
        log_info "You can restore from backup with: cp -r $BACKUP_DIR/* ."
        
        # Ask if user wants to continue despite error
        read -p "Continue despite error? (y/n): " continue_choice
        if [[ $continue_choice != "y" && $continue_choice != "Y" ]]; then
            log_info "Script execution terminated by user after error"
            exit $exit_code
        else
            log_warning "Continuing execution despite error"
        fi
    fi
}

# Set up error trap to call error handler with the line number
trap 'handle_error $LINENO' ERR

# Check if gh CLI is installed and authenticated
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI is not installed. Please install it first: https://cli.github.com/manual/installation"
        exit 1
    fi
    
    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI is not authenticated. Please run 'gh auth login' first"
        exit 1
    fi
    
    log_success "GitHub CLI is installed and authenticated"
}

# Check git configuration
check_git_config() {
    local git_user=$(git config --global user.name)
    local git_email=$(git config --global user.email)
    
    if [[ -z "$git_user" || -z "$git_email" ]]; then
        log_error "Git user.name or user.email is not set"
        log_info "Please configure with:"
        log_info "git config --global user.name \"Your Name\""
        log_info "git config --global user.email \"your-email@example.com\""
        exit 1
    fi
    
    log_success "Git configuration verified: $git_user <$git_email>"
}

# Pulls the latest changes from the repository
pull_repo_changes() {
    log_info "Pulling latest changes from repository"
    
    if git remote -v | grep -q origin; then
        git fetch origin
        git pull origin main --rebase
        log_success "Successfully pulled latest changes"
    else
        log_error "Remote 'origin' not found. Make sure you're in a git repository."
        exit 1
    fi
}

# Commits and pushes changes to the repository
commit_and_push() {
    local commit_message="$1"
    
    log_info "Committing changes with message: $commit_message"
    git add --all
    git commit -m "$commit_message"
    
    log_info "Pushing changes to repository"
    git push origin main
    
    log_success "Successfully committed and pushed changes"
}

# ========================================================================
# VSCode Extension Functions
# ========================================================================

# Sets up the VSCode extension directory
setup_vscode_extension() {
    local extension_path="$EXTENSION_DIR"
    
    log_info "Setting up VSCode extension in $extension_path"
    
    # Create extension directory if it doesn't exist
    mkdir -p "$extension_path/src"
    
    # Remove existing files if needed
    rm -rf "$extension_path/node_modules" "$extension_path/out" 2>/dev/null
    
    # Navigate to extension directory
    cd "$extension_path"
    
    # Initialize npm project if package.json doesn't exist
    if [ ! -f "package.json" ]; then
        log_info "Initializing npm project"
        npm init -y
    fi
    
    # Install necessary dependencies
    log_info "Installing VSCode extension dependencies"
    npm install --save-dev @types/vscode typescript @vscode/test-electron vsce
    
    # Create package.json with correct configuration
    log_info "Creating package.json for VSCode extension"
    cat > package.json << EOL
{
  "name": "$EXTENSION_NAME",
  "displayName": "Hybrid Extension",
  "description": "A VSCode extension for the Hybrid project.",
  "version": "0.0.1",
  "publisher": "$REPO_OWNER",
  "engines": {
    "vscode": "^1.60.0"
  },
  "categories": [
    "Other"
  ],
  "activationEvents": [
    "onCommand:hybrid.helloWorld",
    "onView:hybrid.sidebar"
  ],
  "main": "./out/extension.js",
  "contributes": {
    "commands": [
      {
        "command": "hybrid.helloWorld",
        "title": "Hello World"
      },
      {
        "command": "hybrid.runTests",
        "title": "Run Tests"
      },
      {
        "command": "hybrid.buildProject",
        "title": "Build Project"
      },
      {
        "command": "hybrid.showStatus",
        "title": "Show Hybrid Status"
      }
    ],
    "viewsContainers": {
      "activitybar": [
        {
          "id": "hybrid-sidebar",
          "title": "Hybrid Tools",
          "icon": "resources/icon.png"
        }
      ]
    },
    "views": {
      "hybrid-sidebar": [
        {
          "id": "hybrid.sidebar",
          "name": "Hybrid Controls"
        }
      ]
    }
  },
  "scripts": {
    "vscode:prepublish": "npm run compile",
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./",
    "pretest": "npm run compile",
    "test": "node ./out/test/runTest.js",
    "package": "vsce package"
  },
  "devDependencies": {
    "@types/node": "^16.11.7",
    "@types/vscode": "^1.60.0",
    "@vscode/test-electron": "^2.1.2",
    "typescript": "^4.5.5",
    "vsce": "^2.7.0"
  }
}
EOL
    
    # Create tsconfig.json
    log_info "Creating tsconfig.json for VSCode extension"
    cat > tsconfig.json << EOL
{
  "compilerOptions": {
    "module": "commonjs",
    "target": "ES2020",
    "outDir": "out",
    "lib": ["ES2020"],
    "sourceMap": true,
    "rootDir": "src",
    "strict": true
  },
  "exclude": ["node_modules", ".vscode-test"]
}
EOL
    
    # Create extension.ts file
    log_info "Creating extension.ts file"
    mkdir -p src
    cat > src/extension.ts << EOL
import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  console.log('Congratulations, your extension "hybrid-extension" is now active!');

  // Register the hello world command
  let helloWorldCommand = vscode.commands.registerCommand('hybrid.helloWorld', () => {
    vscode.window.showInformationMessage('Hello World from Hybrid Extension!');
  });
  context.subscriptions.push(helloWorldCommand);

  // Register run tests command
  let runTestsCommand = vscode.commands.registerCommand('hybrid.runTests', () => {
    vscode.window.showInformationMessage('Running Hybrid Tests...');
    // Add actual test runner implementation here
  });
  context.subscriptions.push(runTestsCommand);

  // Register build project command
  let buildProjectCommand = vscode.commands.registerCommand('hybrid.buildProject', () => {
    vscode.window.showInformationMessage('Building Hybrid Project...');
    // Add actual build implementation here
  });
  context.subscriptions.push(buildProjectCommand);

  // Add Status Bar Information
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = 'hybrid.showStatus';
  statusBarItem.text = 'Hybrid Status';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // Register show status command
  let showStatusCommand = vscode.commands.registerCommand('hybrid.showStatus', () => {
    vscode.window.showInformationMessage('Hybrid Extension is active and running!');
  });
  context.subscriptions.push(showStatusCommand);

  // Register sidebar provider
  const sidebarProvider = new SidebarProvider(context.extensionUri);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebarProvider)
  );
}

export function deactivate() {}

class SidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'hybrid.sidebar';
  private _view?: vscode.WebviewView;

  constructor(private readonly _extensionUri: vscode.Uri) {}

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this._extensionUri]
    };

    webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);
    
    // Add event listener for messages from the webview
    webviewView.webview.onDidReceiveMessage(
      message => {
        switch (message.command) {
          case 'alert':
            vscode.window.showInformationMessage(message.text);
            return;
        }
      },
      undefined,
      context.subscriptions
    );
  }

  private _getHtmlForWebview(webview: vscode.Webview): string {
    return \`<!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body {
            padding: 10px;
            color: var(--vscode-foreground);
            font-family: var(--vscode-font-family);
            background-color: var(--vscode-editor-background);
          }
          button {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 8px 12px;
            margin: 5px 0;
            width: 100%;
            cursor: pointer;
            outline: none;
            border-radius: 2px;
          }
          button:hover {
            background-color: var(--vscode-button-hoverBackground);
          }
          h2 {
            margin-top: 5px;
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 5px;
          }
        </style>
        <title>Hybrid Sidebar</title>
      </head>
      <body>
        <h2>Hybrid Controls</h2>
        <button id="runTests">Run Tests</button>
        <button id="buildProject">Build Project</button>
        <button id="showStatus">Show Status</button>
        
        <script>
          const vscode = acquireVsCodeApi();
          
          document.getElementById('runTests').addEventListener('click', () => {
            vscode.postMessage({
              command: 'alert',
              text: 'Running tests...'
            });
            vscode.postMessage({
              command: 'runTests'
            });
          });
          
          document.getElementById('buildProject').addEventListener('click', () => {
            vscode.postMessage({
              command: 'alert',
              text: 'Building project...'
            });
            vscode.postMessage({
              command: 'buildProject'
            });
          });
          
          document.getElementById('showStatus').addEventListener('click', () => {
            vscode.postMessage({
              command: 'alert',
              text: 'Showing status...'
            });
            vscode.postMessage({
              command: 'showStatus'
            });
          });
        </script>
      </body>
      </html>\`;
  }
}
EOL

    # Create resources directory for icons
    mkdir -p resources
    
    # Return to the main directory
    cd ..
    
    log_success "VSCode extension setup completed"
}

# Build the VSCode extension
build_vscode_extension() {
    log_info "Building VSCode extension"
    
    cd "$EXTENSION_DIR"
    npm run compile
    
    if [ $? -eq 0 ]; then
        log_success "VSCode extension built successfully"
    else
        log_error "Failed to build VSCode extension"
        return 1
    fi
    
    # Package the extension
    npm run package
    
    if [ $? -eq 0 ]; then
        log_success "VSCode extension packaged successfully"
    else
        log_warning "Failed to package VSCode extension"
    fi
    
    cd ..
}

# ========================================================================
# Todo List Processing Functions
# ========================================================================

# Parse the todo.md file and get the next highest priority item
get_next_todo_item() {
    if [ ! -f "$TODO_FILE" ]; then
        log_warning "Todo file $TODO_FILE not found"
        return 1
    }
    
    log_info "Parsing todo.md for next highest priority item"
    
    # Look for lines with priority markers (e.g., [HIGH], [MEDIUM], [LOW])
    # and that are not marked as completed
    local next_item=$(grep -i "\[HIGH\]" "$TODO_FILE" | grep -v "~~" | head -n 1)
    
    if [ -z "$next_item" ]; then
        next_item=$(grep -i "\[MEDIUM\]" "$TODO_FILE" | grep -v "~~" | head -n 1)
    fi
    
    if [ -z "$next_item" ]; then
        next_item=$(grep -i "\[LOW\]" "$TODO_FILE" | grep -v "~~" | head -n 1)
    fi
    
    if [ -z "$next_item" ]; then
        # If no priority markers, just get the first non-completed item
        next_item=$(grep -E "^- \[ \]" "$TODO_FILE" | head -n 1)
    fi
    
    if [ -z "$next_item" ]; then
        log_info "No pending todo items found"
        return 1
    fi
    
    echo "$next_item"
    log_info "Next todo item: $next_item"
    return 0
}

# Mark a todo item as completed
mark_todo_completed() {
    local item="$1"
    local escaped_item=$(echo "$item" | sed 's/[\/&]/\\&/g')
    
    log_info "Marking todo item as completed: $item"
    
    # Replace "[ ]" with "[x]" for the specific item
    sed -i "s/$escaped_item/~~$escaped_item~~/g" "$TODO_FILE"
    
    if [ $? -eq 0 ]; then
        log_success "Todo item marked as completed"
        return 0
    else
        log_error "Failed to mark todo item as completed"
        return 1
    fi
}

# Add a new todo item
add_todo_item() {
    local item="$1"
    local priority="${2:-MEDIUM}"  # Default priority is MEDIUM
    
    log_info "Adding new todo item with priority [$priority]: $item"
    
    echo "- [ ] [$priority] $item" >> "$TODO_FILE"
    
    if [ $? -eq 0 ]; then
        log_success "Todo item added successfully"
        return 0
    else
        log_error "Failed to add todo item"
        return 1
    fi
}

# ========================================================================
# Main Functions
# ========================================================================

# Main function to update the repository
update_repository() {
    log_info "Starting repository update process"
    
    # Pull latest changes
    pull_repo_changes
    
    # Setup VSCode extension if it doesn't exist or needs update
    if [ ! -d "$EXTENSION_DIR" ] || [ ! -f "$EXTENSION_DIR/package.json" ]; then
        setup_vscode_extension
        build_vscode_extension
    fi
    
    # Get next todo item and try to work on it
    local next_todo=$(get_next_todo_item)
    if [ $? -eq 0 ]; then
        log_info "Working on next todo item: $next_todo"
        # Implement todo item processing here
        # For now, we'll just mark it as completed
        mark_todo_completed "$next_todo"
    fi
    
    # Commit and push changes
    commit_and_push "Auto-update: VSCode extension and todo list updates"
    
    log_success "Repository update process completed"
}

# Initialize the script
initialize() {
    # Create log file or clear existing one
    echo "=== Hybrid Repository Update Log - $(date) ===" > "$LOG_FILE"
    
    log_info "Initializing repository update script"
    
    # Check required tools
    check_gh_cli
    check_git_config
    
    # Check if we're in the correct directory
    if [ ! -d ".git" ]; then
        log_warning "Not in a git repository. Cloning the repository..."
        git clone "https://github.com/$REPO_OWNER/$REPO_NAME.git"
        cd "$REPO_NAME"
    fi
    
    log_success "Initialization completed"
}

# ========================================================================
# Main Script Execution
# ========================================================================

# Initialize the script
initialize

# Process command line arguments
case "$1" in
    --vscode-only)
        setup_vscode_extension
        build_vscode_extension
        commit_and_push "Update VSCode extension"
        ;;
    --todo-add)
        if [ -z "$2" ]; then
            log_error "Todo item text is required"
            exit 1
        fi
        add_todo_item "$2" "$3"
        commit_and_push "Add todo item: $2"
        ;;
    --todo-list)
        if [ -f "$TODO_FILE" ]; then
            log_info "Todo list items:"
            cat "$TODO_FILE"
        else
            log_error "Todo file not found"
        fi
        ;;
    --help)
        echo "Usage: $0 [OPTION]"
        echo "Automated script for updating the Hybrid Dev Beta repository"
        echo ""
        echo "Options:"
        echo "  --vscode-only       Only update the VSCode extension"
        echo "  --todo-add TEXT     Add a new todo item"
        echo "  --todo-list         Show all todo items"
        echo "  --help              Display this help message"
        echo ""
        echo "Without options, the script will run a full update."
        exit 0
        ;;
    *)
        # Run full update by default
        update_repository
        ;;
esac

log_info "Script execution completed"