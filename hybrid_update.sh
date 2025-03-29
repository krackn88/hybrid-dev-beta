#!/bin/bash
# Complete GitHub automation script with webhook setup for hybrid-dev-beta
# Author: krackn88
# Version: 1.0.0

# ===== COLORS FOR BETTER OUTPUT =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===== CONFIGURATION =====
REPO_OWNER="krackn88"
REPO_NAME="hybrid-dev-beta"
BRANCH="main"
EXTENSION_DIR="vscode-extension"
LOG_FILE="hybrid_updater.log"
WEBHOOK_PORT=8000
NGROK_AUTH_TOKEN="${NGROK_AUTH_TOKEN:-}" # From environment or empty

# Create or set webhook secret if not already in env var
if [ -z "$WEBHOOK_SECRET" ]; then
    WEBHOOK_SECRET=$(openssl rand -hex 20)
    echo -e "${YELLOW}Generated webhook secret: $WEBHOOK_SECRET${NC}"
    echo "Export this to use it in the future:"
    echo "export WEBHOOK_SECRET=$WEBHOOK_SECRET"
fi

# GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}ERROR: GITHUB_TOKEN environment variable is required${NC}"
    echo "Create a personal access token at https://github.com/settings/tokens"
    echo "Then set it with: export GITHUB_TOKEN=your_token_here"
    exit 1
fi

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
        cleanup_ngrok
        exit $exit_code
    fi
}

trap 'handle_error $LINENO' ERR

# ===== ENVIRONMENT CHECK =====
check_dependencies() {
    log_info "Checking required dependencies..."
    
    # Check for git
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install git first."
        exit 1
    fi
    
    # Check for ngrok
    if ! command -v ngrok &> /dev/null; then
        log_error "ngrok is not installed. Please install ngrok first."
        log_info "Install using: npm install -g ngrok"
        exit 1
    fi
    
    # Check for nodejs and npm
    if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
        log_warning "Node.js or npm not found. VSCode extension may not build correctly."
    fi
    
    # Check for jq
    if ! command -v jq &> /dev/null; then
        log_warning "jq not found, installing..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v brew &> /dev/null; then
            brew install jq
        elif command -v yum &> /dev/null; then
            sudo yum install -y jq
        else
            log_error "Could not install jq. Please install it manually."
            exit 1
        fi
    fi
    
    log_success "All required dependencies are available"
}

# ===== REPOSITORY OPERATIONS =====
setup_repository() {
    log_info "Setting up repository..."
    
    # Check if repo directory exists
    if [ ! -d "$REPO_NAME" ]; then
        log_info "Cloning repository..."
        git clone "https://$GITHUB_TOKEN@github.com/$REPO_OWNER/$REPO_NAME.git"
        cd "$REPO_NAME"
    else
        log_info "Repository exists, updating..."
        cd "$REPO_NAME"
        git fetch origin
        git reset --hard origin/$BRANCH
    fi
    
    log_success "Repository setup complete"
}

# ===== VSCODE EXTENSION SETUP =====
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
  "version": "0.0.1",
  "publisher": "$REPO_OWNER",
  "engines": {
    "vscode": "^1.60.0"
  },
  "categories": ["Other"],
  "activationEvents": ["onCommand:hybrid.helloWorld"],
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
      }
    ]
  },
  "scripts": {
    "vscode:prepublish": "npm run compile",
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./",
    "package": "vsce package"
  },
  "devDependencies": {
    "@types/node": "^16.11.7",
    "@types/vscode": "^1.60.0",
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

  // Register hello world command
  let helloCmd = vscode.commands.registerCommand('hybrid.helloWorld', () => {
    vscode.window.showInformationMessage('Hello from Hybrid Extension!');
  });
  context.subscriptions.push(helloCmd);

  // Register run tests command
  let runTestsCmd = vscode.commands.registerCommand('hybrid.runTests', () => {
    vscode.window.showInformationMessage('Running Hybrid Tests...');
  });
  context.subscriptions.push(runTestsCmd);

  // Register build project command
  let buildCmd = vscode.commands.registerCommand('hybrid.buildProject', () => {
    vscode.window.showInformationMessage('Building Hybrid Project...');
  });
  context.subscriptions.push(buildCmd);
}

export function deactivate() {}
EOL

    log_success "VSCode extension files created"
}

build_vscode_extension() {
    log_info "Building VSCode extension..."
    
    cd "$EXTENSION_DIR"
    
    # Install dependencies
    npm install
    
    # Compile extension
    npm run compile
    
    # Return to repo root
    cd ..
    
    log_success "VSCode extension built successfully"
}

# ===== COMMIT AND PUSH CHANGES =====
commit_and_push() {
    local message="$1"
    
    log_info "Committing and pushing changes: $message"
    
    git add .
    git commit -m "$message"
    git push origin $BRANCH
    
    log_success "Changes pushed to GitHub"
}

# ===== WEBHOOK SETUP WITH NGROK =====
start_webhook_server() {
    log_info "Starting webhook server on port $WEBHOOK_PORT..."
    
    # Create webhook server script
    cat > webhook_server.sh << 'EOL'
#!/bin/bash

PORT="${1:-8000}"
SECRET="${WEBHOOK_SECRET}"
LOG_FILE="${2:-webhook_server.log}"

echo "Starting webhook server on port $PORT with secret: $SECRET"
echo "Logging to $LOG_FILE"

# Function to verify GitHub webhook signature
verify_signature() {
    local payload="$1"
    local signature="$2"
    local secret="$3"
    
    # Extract signature algorithm and hash
    local algo=$(echo "$signature" | cut -d'=' -f1)
    local hash=$(echo "$signature" | cut -d'=' -f2)
    
    # Calculate expected signature
    local expected=$(echo -n "$payload" | openssl dgst "-$algo" -hmac "$secret" | awk '{print $2}')
    
    # Compare signatures
    if [ "$hash" = "$expected" ]; then
        return 0
    else
        return 1
    fi
}

# Start listener
while true; do
    echo "Waiting for webhook calls..." | tee -a "$LOG_FILE"
    
    # Use netcat to listen for HTTP requests
    nc -l -p "$PORT" > request.tmp
    
    # Process the request
    {
        # Parse headers and body
        REQUEST=$(cat request.tmp)
        HEADERS=$(echo "$REQUEST" | awk 'BEGIN{RS="\r\n\r\n";ORS=""}1')
        BODY=$(echo "$REQUEST" | awk 'BEGIN{RS="\r\n\r\n";ORS=""}2')
        
        # Extract important headers
        EVENT=$(echo "$HEADERS" | grep -i "X-GitHub-Event:" | cut -d' ' -f2 | tr -d '\r')
        SIGNATURE=$(echo "$HEADERS" | grep -i "X-Hub-Signature-256:" | cut -d' ' -f2 | tr -d '\r')
        
        echo "Received $EVENT event" | tee -a "$LOG_FILE"
        
        # Verify signature
        if [ ! -z "$SIGNATURE" ] && [ ! -z "$SECRET" ]; then
            if verify_signature "$BODY" "$SIGNATURE" "$SECRET"; then
                echo "Signature verification passed" | tee -a "$LOG_FILE"
                # If it's a push event, trigger an update
                if [ "$EVENT" = "push" ]; then
                    echo "Push event detected, triggering update" | tee -a "$LOG_FILE"
                    # Here you would add the commands to update your repo
                    # For now, we just log it
                    echo "Would update repository now" | tee -a "$LOG_FILE"
                fi
            else
                echo "Signature verification failed" | tee -a "$LOG_FILE"
            fi
        else
            echo "Missing signature or secret" | tee -a "$LOG_FILE"
        fi
        
        # Send response
        echo -e "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"received\"}" | nc -l -p "$PORT" >/dev/null
    } &
done
EOL

    chmod +x webhook_server.sh
    
    # Start webhook server in background
    ./webhook_server.sh "$WEBHOOK_PORT" "$LOG_FILE" &
    WEBHOOK_PID=$!
    
    log_success "Webhook server started with PID: $WEBHOOK_PID"
}

start_ngrok() {
    log_info "Starting ngrok tunnel to port $WEBHOOK_PORT..."
    
    # Check if ngrok auth token was provided
    if [ ! -z "$NGROK_AUTH_TOKEN" ]; then
        ngrok authtoken "$NGROK_AUTH_TOKEN" >/dev/null 2>&1
    fi
    
    # Start ngrok in background and capture the URL
    ngrok http "$WEBHOOK_PORT" > /dev/null &
    NGROK_PID=$!
    
    # Wait for ngrok to initialize
    sleep 3
    
    # Get the ngrok public URL
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')
    
    if [ -z "$NGROK_URL" ] || [ "$NGROK_URL" = "null" ]; then
        log_error "Failed to get ngrok URL. Check that ngrok is running properly."
        exit 1
    fi
    
    WEBHOOK_URL="${NGROK_URL}/webhook"
    
    log_success "Ngrok tunnel established: $NGROK_URL"
    log_info "Webhook URL: $WEBHOOK_URL"
}

configure_github_webhook() {
    log_info "Configuring GitHub webhook..."
    
    # Create webhook via GitHub API
    RESPONSE=$(curl -s -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks" \
        -d '{
            "name": "web",
            "active": true,
            "events": ["push"],
            "config": {
                "url": "'$WEBHOOK_URL'",
                "content_type": "json",
                "secret": "'$WEBHOOK_SECRET'"
            }
        }')
    
    # Check response
    if echo "$RESPONSE" | grep -q '"id":'; then
        WEBHOOK_ID=$(echo "$RESPONSE" | jq -r .id)
        log_success "GitHub webhook created with ID: $WEBHOOK_ID"
    else
        log_error "Failed to create GitHub webhook: $(echo "$RESPONSE" | jq -r .message)"
        log_info "You may need to delete existing webhooks or check your token permissions"
    fi
}

cleanup_ngrok() {
    log_info "Cleaning up ngrok and webhook server..."
    
    # Kill ngrok if running
    if [ ! -z "$NGROK_PID" ]; then
        kill -9 $NGROK_PID 2>/dev/null || true
    fi
    
    # Kill webhook server if running
    if [ ! -z "$WEBHOOK_PID" ]; then
        kill -9 $WEBHOOK_PID 2>/dev/null || true
    fi
    
    log_info "Cleanup complete"
}

# ===== MAIN EXECUTION FLOW =====
main() {
    echo -e "${GREEN}====== HYBRID DEV AUTO-UPDATER ======${NC}"
    log_info "Starting auto-updater script"
    
    # Initialize log file
    echo "=== Hybrid Dev Auto-Updater Log - $(date) ===" > "$LOG_FILE"
    
    # Check environment and dependencies
    check_dependencies
    
    # Setup repository
    setup_repository
    
    # Setup VSCode extension
    setup_vscode_extension
    build_vscode_extension
    
    # Commit and push initial changes
    commit_and_push "Update VSCode extension via auto-updater"
    
    # Ask if webhook should be set up
    read -p "Do you want to set up a webhook for real-time updates? (y/n): " setup_webhook
    
    if [[ "$setup_webhook" == "y" ]]; then
        # Start webhook server
        start_webhook_server
        
        # Start ngrok and get public URL
        start_ngrok
        
        # Configure GitHub webhook
        configure_github_webhook
        
        echo -e "${GREEN}====== WEBHOOK SETUP COMPLETE ======${NC}"
        echo "Webhook URL: $WEBHOOK_URL"
        echo "Webhook Secret: $WEBHOOK_SECRET"
        echo ""
        echo "The webhook and ngrok are now running. Press Ctrl+C to stop."
        echo ""
        
        # Keep script running
        trap cleanup_ngrok EXIT
        while true; do sleep 60; done
    else
        log_info "Webhook setup skipped"
        log_success "Script execution completed"
    fi
}

# Execute main function
main

