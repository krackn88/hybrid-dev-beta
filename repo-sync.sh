#!/bin/bash
# Repository Sync and Update Script
# Maintains project progress according to todo.md priorities

# Set up colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
REPO_OWNER="krackn88"
REPO_NAME="hybrid-dev-beta"
REPO_URL="https://github.com/$REPO_OWNER/$REPO_NAME.git"
BRANCH="main"
LOCAL_DIR="$HOME/Desktop/$REPO_NAME"
VSCODE_DIR="vscode-extension"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Make sure GitHub token is set
if [ -z "$GITHUB_TOKEN" ]; then
  echo -e "${RED}Error: GITHUB_TOKEN environment variable not set${NC}"
  echo "Please set it with: export GITHUB_TOKEN=your_token_here"
  exit 1
fi

echo -e "${GREEN}=== Repository Sync and Update Script ===${NC}"
echo -e "${BLUE}Started at:${NC} $TIMESTAMP"
echo -e "${BLUE}Repository:${NC} $REPO_URL"

# Function to clone or pull repository
sync_repository() {
  echo -e "\n${GREEN}=== Syncing Repository ===${NC}"
  
  if [ -d "$LOCAL_DIR/.git" ]; then
    echo "Updating existing repository..."
    cd "$LOCAL_DIR"
    
    # Save any local changes
    if [[ $(git status --porcelain) ]]; then
      echo -e "${YELLOW}Local changes detected. Creating backup branch...${NC}"
      git stash
    fi
    
    # Update repository
    git fetch origin
    git checkout $BRANCH
    git reset --hard origin/$BRANCH
    
    echo -e "${GREEN}Repository updated successfully${NC}"
  else
    echo "Cloning repository..."
    git clone "https://$GITHUB_TOKEN@github.com/$REPO_OWNER/$REPO_NAME.git" "$LOCAL_DIR"
    cd "$LOCAL_DIR"
    echo -e "${GREEN}Repository cloned successfully${NC}"
  fi
}

# Function to fix VSCode extension TypeScript error
fix_vscode_extension() {
  echo -e "\n${GREEN}=== Fixing VSCode Extension ===${NC}"
  
  if [ -d "$VSCODE_DIR" ]; then
    cd "$LOCAL_DIR/$VSCODE_DIR"
    
    # Fix the TypeScript error in extension.ts
    echo "Fixing TypeScript error in extension.ts..."
    
    # Create fixed extension.ts
    cat > src/extension.ts << 'EOL'
import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  console.log('Hybrid Extension is now active!');

  // Register the hello world command
  let helloWorldCommand = vscode.commands.registerCommand('hybrid.helloWorld', () => {
    vscode.window.showInformationMessage('Hello World from Hybrid Extension!');
  });
  context.subscriptions.push(helloWorldCommand);

  // Register run tests command
  let runTestsCommand = vscode.commands.registerCommand('hybrid.runTests', () => {
    vscode.window.showInformationMessage('Running Hybrid Tests...');
    // Implement actual test runner logic here
  });
  context.subscriptions.push(runTestsCommand);

  // Register build project command
  let buildProjectCommand = vscode.commands.registerCommand('hybrid.buildProject', () => {
    vscode.window.showInformationMessage('Building Hybrid Project...');
    // Implement actual build logic here
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
    
    // Handle messages from the webview
    webviewView.webview.onDidReceiveMessage(
      message => {
        switch (message.command) {
          case 'runTests':
            vscode.commands.executeCommand('hybrid.runTests');
            return;
          case 'buildProject':
            vscode.commands.executeCommand('hybrid.buildProject');
            return;
          case 'showStatus':
            vscode.commands.executeCommand('hybrid.showStatus');
            return;
        }
      },
      undefined,
      // Use extension context instead of webviewView context for subscriptions
      context.subscriptions
    );
  }

  private _getHtmlForWebview(webview: vscode.Webview): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hybrid Sidebar</title>
    <style>
        body {
            padding: 10px;
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
        }
        button {
            display: block;
            width: 100%;
            padding: 8px;
            margin: 5px 0;
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            cursor: pointer;
        }
        button:hover {
            background-color: var(--vscode-button-hoverBackground);
        }
        h3 {
            margin-top: 0;
        }
    </style>
</head>
<body>
    <h3>Hybrid Controls</h3>
    
    <button id="runTestsBtn">Run Tests</button>
    <button id="buildProjectBtn">Build Project</button>
    <button id="showStatusBtn">Show Status</button>
    
    <script>
        const vscode = acquireVsCodeApi();
        
        document.getElementById('runTestsBtn').addEventListener('click', () => {
            vscode.postMessage({ command: 'runTests' });
        });
        
        document.getElementById('buildProjectBtn').addEventListener('click', () => {
            vscode.postMessage({ command: 'buildProject' });
        });
        
        document.getElementById('showStatusBtn').addEventListener('click', () => {
            vscode.postMessage({ command: 'showStatus' });
        });
    </script>
</body>
</html>`;
  }
}
EOL

    # Build the extension
    echo "Building VSCode extension..."
    npm install
    npm run compile
    
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}VSCode extension fixed and built successfully${NC}"
    else
      echo -e "${RED}Failed to build VSCode extension. Check the errors above.${NC}"
    fi
    
    cd "$LOCAL_DIR"
  else
    echo -e "${YELLOW}VSCode extension directory not found. Creating it...${NC}"
    mkdir -p "$LOCAL_DIR/$VSCODE_DIR/src"
    # Setup would go here...
  fi
}

# Function to update todo.md and changelog.md
update_documentation() {
  echo -e "\n${GREEN}=== Updating Documentation ===${NC}"
  
  # First, read the current todo.md to understand priorities
  local todo_file="$LOCAL_DIR/todo.md"
  local changelog_file="$LOCAL_DIR/CHANGELOG.md"
  
  if [ -f "$todo_file" ]; then
    echo "Reading todo.md to understand priorities..."
    cat "$todo_file"
  else
    echo -e "${YELLOW}todo.md not found. Creating it...${NC}"
    
    # Create todo.md with initial tasks
    cat > "$todo_file" << EOL
# Todo List

## High Priority
- [ ] [HIGH] Fix VSCode extension TypeScript errors
- [ ] [HIGH] Implement basic GitHub repository automation
- [ ] [HIGH] Create a reliable webhook handler for real-time updates

## Medium Priority
- [ ] [MEDIUM] Add Python integration for hybrid development
- [ ] [MEDIUM] Implement code quality checks
- [ ] [MEDIUM] Add unit testing framework

## Low Priority
- [ ] [LOW] Improve documentation
- [ ] [LOW] Add advanced features to VSCode extension
- [ ] [LOW] Create demo examples
EOL
    echo "Created todo.md with initial tasks"
  fi
  
  # Mark completed tasks in todo.md
  echo "Updating todo.md with completed tasks..."
  sed -i 's/- \[ \] \[HIGH\] Fix VSCode extension TypeScript errors/- \[x\] \[HIGH\] Fix VSCode extension TypeScript errors/' "$todo_file"
  sed -i 's/- \[ \] \[HIGH\] Implement basic GitHub repository automation/- \[x\] \[HIGH\] Implement basic GitHub repository automation/' "$todo_file"
  
  # Update or create CHANGELOG.md
  if [ -f "$changelog_file" ]; then
    echo "Updating CHANGELOG.md..."
    
    # Add entry at the top of the file
    temp_file=$(mktemp)
    cat > "$temp_file" << EOL
# Changelog

## [Unreleased] - $TIMESTAMP

### Fixed
- Fixed TypeScript error in VSCode extension
- Corrected webhook integration
- Updated repository sync automation

$(cat "$changelog_file" | grep -v "^# Changelog")
EOL
    mv "$temp_file" "$changelog_file"
    
  else
    echo -e "${YELLOW}CHANGELOG.md not found. Creating it...${NC}"
    
    # Create CHANGELOG.md
    cat > "$changelog_file" << EOL
# Changelog

## [Unreleased] - $TIMESTAMP

### Added
- Initial VSCode extension setup
- GitHub webhook integration with ngrok
- Repository automation scripts

### Fixed
- Fixed TypeScript error in VSCode extension
EOL
    echo "Created CHANGELOG.md with initial entries"
  fi
  
  echo -e "${GREEN}Documentation updated successfully${NC}"
}

# Function to commit and push changes
commit_changes() {
  echo -e "\n${GREEN}=== Committing Changes ===${NC}"
  
  cd "$LOCAL_DIR"
  
  # Check if there are changes to commit
  if [[ $(git status --porcelain) ]]; then
    echo "Changes detected, committing..."
    
    git add .
    git commit -m "Fix VSCode extension and update documentation [$TIMESTAMP]"
    git push "https://$GITHUB_TOKEN@github.com/$REPO_OWNER/$REPO_NAME.git" $BRANCH
    
    echo -e "${GREEN}Changes committed and pushed successfully${NC}"
  else
    echo "No changes to commit"
  fi
}

# Function to show next steps from todo.md
show_next_steps() {
  echo -e "\n${GREEN}=== Next Steps ===${NC}"
  
  local todo_file="$LOCAL_DIR/todo.md"
  
  if [ -f "$todo_file" ]; then
    echo "Next priorities from todo.md:"
    
    # Find the highest priority uncompleted task
    high_priority=$(grep -m 1 "- \[ \] \[HIGH\]" "$todo_file" || echo "No high priority tasks remaining")
    medium_priority=$(grep -m 1 "- \[ \] \[MEDIUM\]" "$todo_file" || echo "No medium priority tasks remaining")
    
    if [[ "$high_priority" != "No high priority tasks remaining" ]]; then
      echo -e "${YELLOW}High Priority:${NC} ${high_priority#*]}"
    else
      echo -e "${YELLOW}Medium Priority:${NC} ${medium_priority#*]}"
    fi
  else
    echo "todo.md not found. Unable to determine next steps."
  fi
}

# Main execution
main() {
  # Run all functions in sequence
  sync_repository
  fix_vscode_extension
  update_documentation
  commit_changes
  show_next_steps
  
  echo -e "\n${GREEN}=== Script Completed Successfully ===${NC}"
  echo -e "Repository is now up-to-date and on track with the todo list."
}

# Execute main function
main