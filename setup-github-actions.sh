#!/bin/bash
# GitHub Actions Setup Script
# Version: 1.0.0

# ===== CONFIGURATION =====
REPO_DIR="${HOME}/hybrid-dev-beta"
WORKFLOWS_DIR="${REPO_DIR}/.github/workflows"

# ===== FORMATTING =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===== LOGGING FUNCTIONS =====
log() {
    echo -e "$(date +"%Y-%m-%d %H:%M:%S") - $1"
}

log_success() { log "${GREEN}SUCCESS: $1${NC}"; }
log_info() { log "${BLUE}INFO: $1${NC}"; }
log_warning() { log "${YELLOW}WARNING: $1${NC}"; }
log_error() { log "${RED}ERROR: $1${NC}"; }

# ===== SETUP FUNCTIONS =====
setup_ci_workflow() {
    log_info "Setting up CI workflow..."
    
    mkdir -p "$WORKFLOWS_DIR"
    
    cat > "${WORKFLOWS_DIR}/ci.yml" << 'EOL'
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '16'
      
      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install pytest
      
      - name: Install VSCode extension dependencies
        run: |
          if [ -d "vscode-extension" ]; then
            cd vscode-extension
            npm install
          fi
      
      - name: Run tests
        run: |
          if [ -f "./run-tests.sh" ]; then
            chmod +x ./run-tests.sh
            ./run-tests.sh
          else
            echo "No test script found, running basic tests"
            pytest
          fi
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-reports/
EOL
    
    log_success "CI workflow created"
}

setup_release_workflow() {
    log_info "Setting up release workflow..."
    
    mkdir -p "$WORKFLOWS_DIR"
    
    cat > "${WORKFLOWS_DIR}/release.yml" << 'EOL'
name: Release

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Version number (e.g., 1.0.0)'
        required: true
        default: ''

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '16'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          
          if [ -d "vscode-extension" ]; then
            cd vscode-extension
            npm install
            npm install -g vsce
          fi
      
      - name: Set version
        id: set-version
        run: |
          if [ "${{ github.event_name }}" == "workflow_dispatch" ]; then
            VERSION="${{ github.event.inputs.version }}"
          else
            VERSION="${GITHUB_REF#refs/tags/v}"
          fi
          echo "VERSION=$VERSION" >> $GITHUB_ENV
          echo "version=$VERSION" >> $GITHUB_OUTPUT
      
      - name: Build VSCode extension
        if: ${{ success() }}
        run: |
          if [ -d "vscode-extension" ]; then
            cd vscode-extension
            npm version $VERSION --no-git-tag-version
            npm run compile
            vsce package
            echo "VSIX_PATH=$(find . -name '*.vsix' -type f | head -n 1)" >> $GITHUB_ENV
          fi
      
      - name: Create Release
        id: create_release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: v${{ steps.set-version.outputs.version }}
          release_name: Release v${{ steps.set-version.outputs.version }}
          draft: false
          prerelease: false
      
      - name: Upload VSCode Extension
        if: ${{ success() && env.VSIX_PATH != '' }}
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ steps.create_release.outputs.upload_url }}
          asset_path: ${{ env.VSIX_PATH }}
          asset_name: vscode-hybrid-extension-${{ steps.set-version.outputs.version }}.vsix
          asset_content_type: application/octet-stream
EOL
    
    log_success "Release workflow created"
}

setup_webhook_workflow() {
    log_info "Setting up webhook management workflow..."
    
    mkdir -p "$WORKFLOWS_DIR"
    
    cat > "${WORKFLOWS_DIR}/webhook-manager.yml" << 'EOL'
name: Webhook Manager

on:
  workflow_dispatch:
    inputs:
      action:
        description: 'Action to perform'
        required: true
        default: 'list'
        type: choice
        options:
          - list
          - create
          - delete
      webhook_id:
        description: 'Webhook ID (for delete action)'
        required: false
        default: ''

jobs:
  webhook-manager:
    runs-on: ubuntu-latest
    steps:
      - name: List webhooks
        if: ${{ github.event.inputs.action == 'list' }}
        run: |
          echo "Listing existing webhooks..."
          curl -s -H "Authorization: token ${{ secrets.REPO_TOKEN }}" \
               -H "Accept: application/vnd.github.v3+json" \
               "https://api.github.com/repos/${{ github.repository }}/hooks" | \
          jq -r '.[] | "ID: \(.id) | URL: \(.config.url) | Events: \(.events)"'
      
      - name: Create webhook
        if: ${{ github.event.inputs.action == 'create' }}
        run: |
          echo "Creating new webhook..."
          
          # Generate a secure webhook secret
          WEBHOOK_SECRET=$(openssl rand -hex 20)
          
          # Create the webhook
          RESPONSE=$(curl -s -X POST \
                      -H "Authorization: token ${{ secrets.REPO_TOKEN }}" \
                      -H "Accept: application/vnd.github.v3+json" \
                      "https://api.github.com/repos/${{ github.repository }}/hooks" \
                      -d '{
                          "name": "web",
                          "active": true,
                          "events": ["push"],
                          "config": {
                              "url": "https://your-webhook-url.example.com",
                              "content_type": "json",
                              "secret": "'"$WEBHOOK_SECRET"'"
                          }
                      }')
          
          # Extract and display webhook ID
          WEBHOOK_ID=$(echo "$RESPONSE" | jq -r '.id')
          
          if [ "$WEBHOOK_ID" != "null" ]; then
            echo "Webhook created successfully!"
            echo "Webhook ID: $WEBHOOK_ID"
            echo "Webhook Secret: $WEBHOOK_SECRET"
            echo ""
            echo "IMPORTANT: Save this webhook secret securely - it won't be shown again!"
          else
            echo "Error creating webhook:"
            echo "$RESPONSE" | jq
            exit 1
          fi
      
      - name: Delete webhook
        if: ${{ github.event.inputs.action == 'delete' && github.event.inputs.webhook_id != '' }}
        run: |
          echo "Deleting webhook ID: ${{ github.event.inputs.webhook_id }}"
          
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
                       -X DELETE \
                       -H "Authorization: token ${{ secrets.REPO_TOKEN }}" \
                       -H "Accept: application/vnd.github.v3+json" \
                       "https://api.github.com/repos/${{ github.repository }}/hooks/${{ github.event.inputs.webhook_id }}")
          
          if [ "$STATUS" -eq 204 ]; then
            echo "Webhook deleted successfully!"
          else
            echo "Error deleting webhook. HTTP Status: $STATUS"
            exit 1
          fi
EOL
    
    log_success "Webhook management workflow created"
}

commit_and_push_workflows() {
    log_info "Committing and pushing workflows..."
    
    cd "$REPO_DIR"
    
    # Check if there are changes
    if git status --porcelain | grep -q ".github/workflows"; then
        git add .github/workflows/*.yml
        git commit -m "Add GitHub Actions workflows"
        
        if [ -n "$GITHUB_TOKEN" ]; then
            git push "https://$GITHUB_TOKEN@github.com/krackn88/hybrid-dev-beta.git" main
            log_success "Workflows pushed to GitHub"
        else
            log_warning "GITHUB_TOKEN not set. Please push changes manually."
            log_info "Run: git push origin main"
        fi
    else
        log_info "No workflow changes to commit"
    fi
}

# ===== MAIN EXECUTION =====
main() {
    log_info "Setting up GitHub Actions workflows..."
    
    # Check if repository exists
    if [ ! -d "$REPO_DIR" ]; then
        log_error "Repository directory not found: $REPO_DIR"
        exit 1
    fi
    
    # Set up workflows
    setup_ci_workflow
    setup_release_workflow
    setup_webhook_workflow
    
    # Commit and push
    commit_and_push_workflows
    
    log_success "GitHub Actions setup completed!"
    log_info "Workflows added:"
    log_info "  - CI: Runs tests on push and pull requests"
    log_info "  - Release: Creates releases when tags are pushed"
    log_info "  - Webhook Manager: Manages GitHub webhooks via workflow dispatch"
}

# Run main function
main