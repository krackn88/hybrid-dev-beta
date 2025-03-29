#!/bin/bash
# Comprehensive GitHub Repository Updater with Webhook Support
# Version: 2.0.0

# ===== CONFIGURATION =====
REPO_OWNER="krackn88"
REPO_NAME="hybrid-dev-beta"
BRANCH="main"
EXTENSION_DIR="vscode-extension"
WEBHOOK_PORT=8000
LOG_FILE="hybrid_updater.log"
WORKING_DIR="$HOME/$REPO_NAME"

# ===== FORMATTING =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===== LOGGING FUNCTIONS =====
log() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${timestamp} - $1" | tee -a "$LOG_FILE"
}

log_success() { log "${GREEN}SUCCESS: $1${NC}"; }
log_info() { log "${BLUE}INFO: $1${NC}"; }
log_warning() { log "${YELLOW}WARNING: $1${NC}"; }
log_error() { log "${RED}ERROR: $1${NC}"; }

# ===== ERROR HANDLING =====
handle_error() {
    local exit_code=$?
    local line_number=$1
    
    if [ $exit_code -ne 0 ]; then
        log_error "Failed at line $line_number with exit code $exit_code"
        
        # Check if cleanup is needed
        if [ ! -z "$NGROK_PID" ]; then
            cleanup_processes
        fi
        
        # Ask if user wants to continue
        read -p "Continue despite error? (y/n): " continue_choice
        if [[ $continue_choice != "y" && $continue_choice != "Y" ]]; then
            exit $exit_code
        fi
    fi
}

trap 'handle_error $LINENO' ERR

# ===== PRE-FLIGHT CHECKS =====
check_requirements() {
    log_info "Checking requirements..."
    
    # Check for GitHub token
    if [ -z "$GITHUB_TOKEN" ]; then
        log_error "GITHUB_TOKEN environment variable not set"
        log_info "Set it with: export GITHUB_TOKEN=your_token_here"
        exit 1
    fi
    
    # Check for required tools
    for cmd in git jq ngrok curl; do
        if ! command -v $cmd &> /dev/null; then
            log_error "$cmd is required but not installed"
            exit 1
        fi
    done
    
    # Check for Node.js and npm (needed for VSCode extension)
    if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
        log_warning "Node.js or npm not found. VSCode extension building may fail."
    fi
    
    # Validate GitHub token has required permissions
    validate_github_token
    
    log_success "All requirements satisfied"
}

validate_github_token() {
    log_info "Validating GitHub token..."
    
    # Test GitHub API access
    local response=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
                       -H "Accept: application/vnd.github.v3+json" \
                       "https://api.github.com/user")
    
    if echo "$response" | grep -q "Bad credentials"; then
        log_error "GitHub token is invalid"
        exit 1
    elif ! echo "$response" | grep -q "login"; then
        log_error "GitHub API request failed: $(echo "$response" | jq -r '.message // "Unknown error"')"
        exit 1
    fi
    
    log_success "GitHub token is valid"
}

# ===== REPOSITORY OPERATIONS =====
setup_repository() {
    log_info "Setting up repository..."
    
    # Create working directory if it doesn't exist
    mkdir -p "$WORKING_DIR"
    
    # Check if repo already exists
    if [ -d "$WORKING_DIR/.git" ]; then
        log_info "Repository exists, updating..."
        cd "$WORKING_DIR"
        
        # Check if we have the right repository
        local remote_url=$(git config --get remote.origin.url)
        if [[ "$remote_url" != *"$REPO_OWNER/$REPO_NAME"* ]]; then
            log_warning "Directory contains a different repository. Recloning..."
            cd ..
            rm -rf "$WORKING_DIR"
            git clone "https://$GITHUB_TOKEN@github.com/$REPO_OWNER/$REPO_NAME.git" "$WORKING_DIR"
            cd "$WORKING_DIR"
        else
            # Update existing repository
            git fetch origin
            git checkout $BRANCH
            git reset --hard origin/$BRANCH
        fi
    else
        log_info "Cloning repository..."
        git clone "https://$GITHUB_TOKEN@github.com/$REPO_OWNER/$REPO_NAME.git" "$WORKING_DIR"
        cd "$WORKING_DIR"
    fi
    
    log_success "Repository ready at $WORKING_DIR"
}

# ===== VSCODE EXTENSION FUNCTIONS =====
setup_vscode_extension() {
    log_info "Setting up VSCode extension..."
    
    # Create extension directory
    mkdir -p "$EXTENSION_DIR/src"
    
    # Create package.json
    cat > "$EXTENSION_DIR/package.json" << EOL
{
  "name": "vscode-hybrid-extension",
  "displayName": "Hybrid Extension",
  "description": "A VSCode extension for the Hybrid project.",
  "version": "0.0.2",
  "publisher": "$REPO_OWNER",
  "engines": {
    "vscode": "^1.60.0"
  },
  "categories": ["Other"],
  "activationEvents": [
    "onCommand:hybrid.helloWorld",
    "onCommand:hybrid.runTests",
    "onCommand:hybrid.buildProject",
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
        "title": "Run Hybrid Tests"
      },
      {
        "command": "hybrid.buildProject",
        "title": "Build Hybrid Project"
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
    cat > "$EXTENSION_DIR/tsconfig.json" << EOL
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
    
    # Create extension.ts
    cat > "$EXTENSION_DIR/src/extension.ts" << EOL
import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  console.log('Hybrid Extension is now active!');

  // Register commands
  const commands = [
    vscode.commands.registerCommand('hybrid.helloWorld', () => {
      vscode.window.showInformationMessage('Hello from Hybrid Extension!');
    }),
    
    vscode.commands.registerCommand('hybrid.runTests', () => {
      vscode.window.showInformationMessage('Running Hybrid Tests...');
      // Implement actual test runner logic here
    }),
    
    vscode.commands.registerCommand('hybrid.buildProject', () => {
      vscode.window.showInformationMessage('Building Hybrid Project...');
      // Implement actual build logic here
    }),
    
    vscode.commands.registerCommand('hybrid.showStatus', () => {
      vscode.window.showInformationMessage('Hybrid Extension Status: Active');
    })
  ];
  
  // Register all commands
  commands.forEach(command => context.subscriptions.push(command));
  
  // Add Status Bar Item
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = 'hybrid.showStatus';
  statusBarItem.text = 'Hybrid Status';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);
  
  // Register sidebar provider
  const sidebarProvider = new SidebarProvider(context.extensionUri);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebarProvider)
  );
}

export function deactivate() {}

class SidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'hybrid.sidebar';
  
  constructor(private readonly _extensionUri: vscode.Uri) {}
  
  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this._extensionUri]
    };
    
    webviewView.webview.html = this._getHtmlForWebview();
    
    // Handle messages from the webview
    webviewView.webview.onDidReceiveMessage(
      message => {
        switch (message.command) {
          case 'runTests':
            vscode.commands.executeCommand('hybrid.runTests');
            break;
          case 'buildProject':
            vscode.commands.executeCommand('hybrid.buildProject');
            break;
          case 'showStatus':
            vscode.commands.executeCommand('hybrid.showStatus');
            break;
        }
      },
      undefined,
      context.subscriptions
    );
  }
  
  private _getHtmlForWebview(): string {
    return \`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      padding: 10px;
      font-family: var(--vscode-font-family);
      color: var(--vscode-foreground);
    }
    .control-button {
      width: 100%;
      padding: 8px;
      margin: 5px 0;
      background-color: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
      border: none;
      cursor: pointer;
    }
    .control-button:hover {
      background-color: var(--vscode-button-hoverBackground);
    }
    h3 {
      margin-top: 0;
    }
  </style>
</head>
<body>
  <h3>Hybrid Controls</h3>
  
  <button class="control-button" id="runTestsBtn">
    Run Tests
  </button>
  
  <button class="control-button" id="buildProjectBtn">
    Build Project
  </button>
  
  <button class="control-button" id="showStatusBtn">
    Show Status
  </button>
  
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
</html>\`;
  }
}
EOL
    
    # Create resources directory and add placeholder icon
    mkdir -p "$EXTENSION_DIR/resources"
    
    # Create a small 1x1 transparent PNG icon (base64 encoded) if it doesn't exist
    if [ ! -f "$EXTENSION_DIR/resources/icon.png" ]; then
        echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFeAJ5g7IQpAAAAABJRU5ErkJggg==" | base64 -d > "$EXTENSION_DIR/resources/icon.png"
    fi
    
    log_success "VSCode extension setup completed"
}

build_vscode_extension() {
    log_info "Building VSCode extension..."
    
    # Navigate to extension directory
    cd "$WORKING_DIR/$EXTENSION_DIR"
    
    # Install dependencies
    npm install --quiet
    
    # Build extension
    npm run compile
    
    # Package extension
    if command -v vsce &> /dev/null; then
        npm run package
    else
        log_warning "vsce not found, skipping packaging step"
    fi
    
    # Return to working directory
    cd "$WORKING_DIR"
    
    log_success "VSCode extension built successfully"
}

# ===== WEBHOOK & NGROK FUNCTIONS =====
generate_webhook_secret() {
    # Generate a secure random webhook secret
    if [ -z "$WEBHOOK_SECRET" ]; then
        WEBHOOK_SECRET=$(openssl rand -hex 20)
        log_info "Generated webhook secret: $WEBHOOK_SECRET"
        log_info "Save this for future use with: export WEBHOOK_SECRET=$WEBHOOK_SECRET"
    else
        log_info "Using existing webhook secret from environment"
    fi
}

start_webhook_server() {
    log_info "Starting webhook server on port $WEBHOOK_PORT..."
    
    # Create webhook server file
    cat > webhook_server.sh << 'EOL'
#!/bin/bash

PORT="${1:-8000}"
SECRET="${WEBHOOK_SECRET}"
REPO_DIR="${2:-$PWD}"
LOG_FILE="${3:-webhook_server.log}"

echo "Starting webhook server on port $PORT"
echo "Repository directory: $REPO_DIR"
echo "Logging to: $LOG_FILE"

process_github_event() {
    local event_type="$1"
    local payload="$2"
    
    echo "$(date +"%Y-%m-%d %H:%M:%S") - Received $event_type event" >> "$LOG_FILE"
    
    # Handle different event types
    if [ "$event_type" = "push" ]; then
        echo "$(date +"%Y-%m-%d %H:%M:%S") - Processing push event" >> "$LOG_FILE"
        cd "$REPO_DIR"
        
        # Pull latest changes
        git fetch origin
        git reset --hard origin/main
        
        # If webhook triggered VSCode extension update, build it
        if [ -d "vscode-extension" ]; then
            echo "$(date +"%Y-%m-%d %H:%M:%S") - Rebuilding VSCode extension" >> "$LOG_FILE"
            cd vscode-extension
            npm install --quiet
            npm run compile
            cd ..
        fi
        
        echo "$(date +"%Y-%m-%d %H:%M:%S") - Repository updated successfully" >> "$LOG_FILE"
    elif [ "$event_type" = "ping" ]; then
        echo "$(date +"%Y-%m-%d %H:%M:%S") - Received ping event - webhook connection successful" >> "$LOG_FILE"
    else
        echo "$(date +"%Y-%m-%d %H:%M:%S") - Ignoring $event_type event" >> "$LOG_FILE"
    fi
}

verify_signature() {
    local payload="$1"
    local signature="$2"
    
    # Extract algorithm and hash
    local algo=$(echo "$signature" | cut -d '=' -f1)
    local received_hash=$(echo "$signature" | cut -d '=' -f2)
    
    # Calculate expected hash
    local expected_hash=$(echo -n "$payload" | openssl dgst "-$algo" -hmac "$SECRET" | awk '{print $2}')
    
    # Compare hashes
    if [ "$received_hash" = "$expected_hash" ]; then
        return 0  # Success
    else
        return 1  # Failure
    fi
}

echo "Webhook server started" >> "$LOG_FILE"

# Simple HTTP server using netcat
while true; do
    # Listen for incoming connections
    HTTP_REQUEST=$(nc -l "$PORT")
    
    # Parse request
    HTTP_METHOD=$(echo "$HTTP_REQUEST" | head -n 1 | cut -d ' ' -f 1)
    
    if [ "$HTTP_METHOD" = "POST" ]; then
        # Extract headers and body
        HTTP_HEADERS=$(echo "$HTTP_REQUEST" | awk 'BEGIN{RS="\r\n\r\n"; ORS=""} {print $0}')
        HTTP_BODY=$(echo "$HTTP_REQUEST" | awk 'BEGIN{RS="\r\n\r\n"; ORS=""} {getline; print $0}')
        
        # Extract GitHub headers
        EVENT_TYPE=$(echo "$HTTP_HEADERS" | grep -i "X-GitHub-Event:" | cut -d ' ' -f 2 | tr -d '\r')
        SIGNATURE=$(echo "$HTTP_HEADERS" | grep -i "X-Hub-Signature-256:" | cut -d ' ' -f 2 | tr -d '\r')
        
        # Verify signature if secret is set
        if [ -n "$SECRET" ] && [ -n "$SIGNATURE" ]; then
            if verify_signature "$HTTP_BODY" "$SIGNATURE"; then
                echo "$(date +"%Y-%m-%d %H:%M:%S") - Signature verified successfully" >> "$LOG_FILE"
                process_github_event "$EVENT_TYPE" "$HTTP_BODY"
            else
                echo "$(date +"%Y-%m-%d %H:%M:%S") - Signature verification failed" >> "$LOG_FILE"
            fi
        else
            echo "$(date +"%Y-%m-%d %H:%M:%S") - No signature verification performed" >> "$LOG_FILE"
            process_github_event "$EVENT_TYPE" "$HTTP_BODY"
        fi
        
        # Send response
        echo -e "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"success\"}" | nc -l "$PORT" &>/dev/null
    else
        # Send response for non-POST requests
        echo -e "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nGitHub Webhook Server" | nc -l "$PORT" &>/dev/null
    fi
done
EOL

    chmod +x webhook_server.sh
    
    # Start webhook server in background
    ./webhook_server.sh "$WEBHOOK_PORT" "$WORKING_DIR" "webhook_server.log" &
    WEBHOOK_PID=$!
    
    log_info "Webhook server started with PID: $WEBHOOK_PID"
}

start_ngrok() {
    log_info "Starting ngrok tunnel to port $WEBHOOK_PORT..."
    
    # Start ngrok in background
    ngrok http "$WEBHOOK_PORT" --log=stdout &> ngrok.log &
    NGROK_PID=$!
    
    # Wait for ngrok to initialize
    sleep 5
    
    # Extract public URL from ngrok API
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')
    
    if [ -z "$NGROK_URL" ] || [ "$NGROK_URL" = "null" ]; then
        log_error "Failed to get ngrok URL. Check ngrok.log for details."
        cat ngrok.log
        exit 1
    fi
    
    WEBHOOK_URL="${NGROK_URL}/webhook"
    
    log_success "Ngrok tunnel established: $NGROK_URL"
    log_info "Webhook URL: $WEBHOOK_URL"
}

setup_github_webhook() {
    log_info "Setting up GitHub webhook..."
    
    # Delete existing webhooks first
    log_info "Checking for existing webhooks..."
    
    local hooks_response=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
                         -H "Accept: application/vnd.github.v3+json" \
                         "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks")
    
    # Extract webhook IDs
    local webhook_ids=$(echo "$hooks_response" | jq -r '.[] | select(.config.url | contains("ngrok")) | .id')
    
    # Delete old ngrok webhooks
    if [ ! -z "$webhook_ids" ]; then
        log_info "Removing old ngrok webhooks..."
        
        for hook_id in $webhook_ids; do
            curl -s -X DELETE \
                 -H "Authorization: token $GITHUB_TOKEN" \
                 -H "Accept: application/vnd.github.v3+json" \
                 "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks/$hook_id"
            
            log_info "Deleted webhook ID: $hook_id"
        done
    fi
    
    # Create new webhook
    log_info "Creating new webhook..."
    
    local create_response=$(curl -s -X POST \
                          -H "Authorization: token $GITHUB_TOKEN" \
                          -H "Accept: application/vnd.github.v3+json" \
                          -H "Content-Type: application/json" \
                          "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks" \
                          -d '{
                              "name": "web",
                              "active": true,
                              "events": ["push"],
                              "config": {
                                  "url": "'$WEBHOOK_URL'",
                                  "content_type": "json",
                                  "insecure_ssl": "0",
                                  "secret": "'$WEBHOOK_SECRET'"
                              }
                          }')
    
    # Verify webhook creation
    if echo "$create_response" | jq -e '.id' &>/dev/null; then
        local webhook_id=$(echo "$create_response" | jq -r '.id')
        log_success "GitHub webhook created successfully with ID: $webhook_id"
    else
        log_error "Failed to create webhook: $(echo "$create_response" | jq -r '.message')"
        return 1
    fi
    
    # Test webhook with ping event
    log_info "Testing webhook with ping event..."
    
    local ping_response=$(curl -s -X POST \
                        -H "Authorization: token $GITHUB_TOKEN" \
                        -H "Accept: application/vnd.github.v3+json" \
                        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks/$webhook_id/pings")
    
    log_success "Webhook setup completed"
}

# ===== COMMIT AND PUSH CHANGES =====
commit_and_push_changes() {
    log_info "Committing and pushing changes..."
    
    # Check if there are changes to commit
    if git status --porcelain | grep -q .; then
        # Add all changes
        git add .
        
        # Create commit message with timestamp
        local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
        local commit_message="Auto-update: VSCode extension [$timestamp]"
        
        # Commit changes
        git commit -m "$commit_message"
        
        # Push to GitHub
        git push "https://$GITHUB_TOKEN@github.com/$REPO_OWNER/$REPO_NAME.git" $BRANCH
        
        log_success "Changes committed and pushed successfully"
    else
        log_info "No changes to commit"
    fi
}

# ===== CLEANUP FUNCTIONS =====
cleanup_processes() {
    log_info "Cleaning up processes..."
    
    # Kill ngrok if running
    if [ ! -z "$NGROK_PID" ]; then
        kill $NGROK_PID 2>/dev/null || true
        log_info "Terminated ngrok process"
    fi
    
    # Kill webhook server if running
    if [ ! -z "$WEBHOOK_PID" ]; then
        kill $WEBHOOK_PID 2>/dev/null || true
        log_info "Terminated webhook server process"
    fi
    
    log_success "Cleanup completed"
}

# ===== MAIN EXECUTION =====
main() {
    # Initialize log file
    echo "=== Hybrid Repository Updater Log - $(date) ===" > "$LOG_FILE"
    
    log_info "Starting Hybrid Repository Updater..."
    
    # Check requirements
    check_requirements
    
    # Setup repository
    setup_repository
    
    # Setup and build VSCode extension
    setup_vscode_extension
    build_vscode_extension
    
    # Commit and push initial changes
    commit_and_push_changes
    
    # Setup webhook with ngrok
    generate_webhook_secret
    start_webhook_server
    start_ngrok
    setup_github_webhook
    
    # Show summary
    log_info "================================================="
    log_info "Setup completed successfully!"
    log_info "Webhook URL: $WEBHOOK_URL"
    log_info "Webhook Secret: $WEBHOOK_SECRET"
    log_info "Working Directory: $WORKING_DIR"
    log_info "================================================="
    log_info "Press Ctrl+C to stop the webhook server and ngrok"
    
    # Keep script running and handle shutdown gracefully
    trap cleanup_processes EXIT INT TERM
    
    # Keep script running until interrupted
    while true; do
        sleep 60
    done
}

# Run the main function
main