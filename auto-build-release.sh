#!/bin/bash
# Auto-Build and Release Script - Triggered by webhook events
# Version: 1.0.0

# ===== CONFIGURATION =====
REPO_OWNER="krackn88"
REPO_NAME="hybrid-dev-beta"
BRANCH="main"
WORKING_DIR="${HOME}/${REPO_NAME}"
LOG_FILE="${WORKING_DIR}/build_release.log"
WEBHOOK_SECRET="bb18eb81289f7b5cc8e195e7f415b2647b7dd22b"
VERSION_FILE="version.txt"

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
        # Send notification of failure (optional)
        send_notification "Build failed at line $line_number with exit code $exit_code"
        exit $exit_code
    fi
}

trap 'handle_error $LINENO' ERR

# ===== HELPER FUNCTIONS =====
check_git_repo() {
    if [ ! -d "$WORKING_DIR/.git" ]; then
        log_error "$WORKING_DIR is not a git repository"
        exit 1
    fi
}

update_repository() {
    log_info "Updating repository..."
    cd "$WORKING_DIR"
    
    # Fetch latest changes
    git fetch origin
    git checkout $BRANCH
    git pull origin $BRANCH
    
    log_success "Repository updated"
}

get_current_version() {
    if [ -f "$VERSION_FILE" ]; then
        cat "$VERSION_FILE"
    else
        echo "0.0.1"
    fi
}

increment_version() {
    local version=$1
    local major minor patch
    
    # Split version into components
    IFS='.' read -r major minor patch <<< "$version"
    
    # Increment patch version
    patch=$((patch + 1))
    
    echo "$major.$minor.$patch"
}

update_version_file() {
    local new_version=$1
    echo "$new_version" > "$VERSION_FILE"
    log_info "Updated version to $new_version"
}

build_vscode_extension() {
    log_info "Building VSCode extension..."
    
    cd "$WORKING_DIR/vscode-extension"
    
    # Install dependencies
    npm install --quiet
    
    # Update version in package.json
    local version=$(get_current_version)
    npm version "$version" --no-git-tag-version
    
    # Build extension
    npm run compile
    
    # Package extension
    npm run package
    
    log_success "VSCode extension built successfully"
    
    # Return generated vsix file path
    find . -name "*.vsix" -type f -print -quit
}

create_github_release() {
    local version=$1
    local vsix_file=$2
    
    log_info "Creating GitHub release for v$version..."
    
    # Create a new tag
    git tag -a "v$version" -m "Release v$version"
    git push origin "v$version"
    
    # Create GitHub release
    local release_json=$(curl -s -X POST \
                      -H "Authorization: token $GITHUB_TOKEN" \
                      -H "Accept: application/vnd.github.v3+json" \
                      -H "Content-Type: application/json" \
                      "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases" \
                      -d '{
                          "tag_name": "v'"$version"'",
                          "name": "Release v'"$version"'",
                          "body": "Automatic release v'"$version"' created by build system",
                          "draft": false,
                          "prerelease": false
                      }')
    
    # Extract release ID
    local release_id=$(echo "$release_json" | jq -r '.id')
    
    if [ "$release_id" = "null" ]; then
        log_error "Failed to create release: $(echo "$release_json" | jq -r '.message')"
        return 1
    fi
    
    # Upload VSCode extension as asset
    if [ -n "$vsix_file" ] && [ -f "$vsix_file" ]; then
        local asset_name=$(basename "$vsix_file")
        
        curl -s -X POST \
             -H "Authorization: token $GITHUB_TOKEN" \
             -H "Accept: application/vnd.github.v3+json" \
             -H "Content-Type: application/octet-stream" \
             --data-binary @"$vsix_file" \
             "https://uploads.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/$release_id/assets?name=$asset_name"
        
        log_success "Uploaded $asset_name to release"
    else
        log_warning "No VSCode extension package found to upload"
    fi
    
    log_success "GitHub release v$version created successfully"
}

send_notification() {
    local message="$1"
    
    # Add your preferred notification method here (Slack, Discord, Email, etc.)
    # Example for Discord webhook (if configured):
    # if [ ! -z "$DISCORD_WEBHOOK_URL" ]; then
    #     curl -s -X POST -H "Content-Type: application/json" \
    #          -d "{\"content\":\"$message\"}" \
    #          "$DISCORD_WEBHOOK_URL"
    # fi
    
    log_info "Notification sent: $message"
}

# ===== MAIN EXECUTION =====
main() {
    # Initialize log
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "=== Auto-Build and Release Log - $(date) ===" > "$LOG_FILE"
    
    log_info "Starting auto-build and release process"
    
    # Check GitHub token
    if [ -z "$GITHUB_TOKEN" ]; then
        log_error "GITHUB_TOKEN environment variable not set"
        exit 1
    fi
    
    # Validate working directory
    check_git_repo
    
    # Update repository
    update_repository
    
    # Get current version and increment it
    local current_version=$(get_current_version)
    local new_version=$(increment_version "$current_version")
    log_info "Incrementing version: $current_version -> $new_version"
    
    # Update version file
    update_version_file "$new_version"
    
    # Commit version change
    cd "$WORKING_DIR"
    git add "$VERSION_FILE"
    git commit -m "Bump version to $new_version [skip ci]"
    git push origin $BRANCH
    
    # Build VSCode extension
    local vsix_file=$(build_vscode_extension)
    
    # Create GitHub release with assets
    create_github_release "$new_version" "$vsix_file"
    
    # Send success notification
    send_notification "🚀 Successfully released v$new_version of hybrid-dev-beta"
    
    log_success "Auto-build and release process completed"
}

# Run main function
main