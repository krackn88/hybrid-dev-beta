#!/bin/bash
# Webhook Management Script
# Version: 1.0.0

# ===== CONFIGURATION =====
REPO_OWNER="krackn88"
REPO_NAME="hybrid-dev-beta"
WEBHOOK_PORT=8000
NGROK_URL="https://1257-2600-2b00-a262-ff00-f43f-fd5e-77af-f19.ngrok-free.app"
WEBHOOK_PATH="/webhook"
WEBHOOK_SECRET="bb18eb81289f7b5cc8e195e7f415b2647b7dd22b"
LOG_FILE="webhook_manager.log"

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

# ===== HELPER FUNCTIONS =====
check_github_token() {
    if [ -z "$GITHUB_TOKEN" ]; then
        log_error "GITHUB_TOKEN environment variable not set"
        log_info "Set it with: export GITHUB_TOKEN=your_token_here"
        exit 1
    fi
}

check_ngrok_running() {
    if ! curl -s "http://localhost:4040/api/tunnels" | grep -q "ngrok"; then
        log_error "ngrok is not running. Please start it with: ngrok http $WEBHOOK_PORT"
        exit 1
    fi
}

get_ngrok_url() {
    local url=$(curl -s "http://localhost:4040/api/tunnels" | jq -r '.tunnels[0].public_url')
    echo "$url"
}

list_webhooks() {
    log_info "Listing GitHub webhooks..."
    
    local response=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
                       -H "Accept: application/vnd.github.v3+json" \
                       "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks")
    
    echo -e "\n${BLUE}Current Webhooks:${NC}"
    echo "$response" | jq -r '.[] | "ID: \(.id) | URL: \(.config.url) | Events: \(.events)"'
    echo ""
}

create_webhook() {
    log_info "Creating GitHub webhook..."
    
    # Get the webhook URL (from ngrok or parameter)
    local webhook_url="$1"
    if [ -z "$webhook_url" ]; then
        check_ngrok_running
        webhook_url="$(get_ngrok_url)$WEBHOOK_PATH"
    fi
    
    # Create the webhook
    local response=$(curl -s -X POST \
                     -H "Authorization: token $GITHUB_TOKEN" \
                     -H "Accept: application/vnd.github.v3+json" \
                     "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks" \
                     -d '{
                         "name": "web",
                         "active": true,
                         "events": ["push"],
                         "config": {
                             "url": "'"$webhook_url"'",
                             "content_type": "json",
                             "secret": "'"$WEBHOOK_SECRET"'"
                         }
                     }')
    
    # Extract webhook ID
    local webhook_id=$(echo "$response" | jq -r '.id')
    
    if [ "$webhook_id" != "null" ]; then
        log_success "Webhook created successfully"
        log_info "Webhook ID: $webhook_id"
        log_info "Webhook URL: $webhook_url"
        log_info "Webhook Secret: $WEBHOOK_SECRET"
    else
        log_error "Failed to create webhook: $(echo "$response" | jq -r '.message')"
        exit 1
    fi
}

delete_webhook() {
    local webhook_id="$1"
    
    if [ -z "$webhook_id" ]; then
        log_error "Webhook ID is required"
        return 1
    fi
    
    log_info "Deleting webhook with ID: $webhook_id"
    
    local status=$(curl -s -o /dev/null -w "%{http_code}" \
                 -X DELETE \
                 -H "Authorization: token $GITHUB_TOKEN" \
                 -H "Accept: application/vnd.github.v3+json" \
                 "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks/$webhook_id")
    
    if [ "$status" -eq 204 ]; then
        log_success "Webhook deleted successfully"
    else
        log_error "Failed to delete webhook. HTTP Status: $status"
        return 1
    fi
}

test_webhook() {
    local webhook_id="$1"
    
    if [ -z "$webhook_id" ]; then
        log_error "Webhook ID is required"
        return 1
    fi
    
    log_info "Testing webhook with ID: $webhook_id"
    
    local response=$(curl -s -X POST \
                   -H "Authorization: token $GITHUB_TOKEN" \
                   -H "Accept: application/vnd.github.v3+json" \
                   "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks/$webhook_id/pings")
    
    local status=$?
    
    if [ $status -eq 0 ]; then
        log_success "Webhook ping sent successfully"
    else
        log_error "Failed to send webhook ping"
        return 1
    fi
}

update_webhook_url() {
    local webhook_id="$1"
    local new_url="$2"
    
    if [ -z "$webhook_id" ]; then
        log_error "Webhook ID is required"
        return 1
    fi
    
    if [ -z "$new_url" ]; then
        check_ngrok_running
        new_url="$(get_ngrok_url)$WEBHOOK_PATH"
    fi
    
    log_info "Updating webhook ID $webhook_id with new URL: $new_url"
    
    local response=$(curl -s -X PATCH \
                   -H "Authorization: token $GITHUB_TOKEN" \
                   -H "Accept: application/vnd.github.v3+json" \
                   "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/hooks/$webhook_id" \
                   -d '{
                       "config": {
                           "url": "'"$new_url"'",
                           "content_type": "json",
                           "secret": "'"$WEBHOOK_SECRET"'"
                       }
                   }')
    
    local updated_url=$(echo "$response" | jq -r '.config.url')
    
    if [ "$updated_url" = "$new_url" ]; then
        log_success "Webhook URL updated successfully"
    else
        log_error "Failed to update webhook URL: $(echo "$response" | jq -r '.message')"
        return 1
    fi
}

# ===== MAIN EXECUTION =====
main() {
    # Initialize log
    echo "=== Webhook Manager Log - $(date) ===" > "$LOG_FILE"
    
    log_info "Webhook Manager Script"
    
    # Check GitHub token
    check_github_token
    
    # Parse command
    local command="$1"
    
    case "$command" in
        list)
            list_webhooks
            ;;
        create)
            local url="$2"
            create_webhook "$url"
            ;;
        delete)
            local webhook_id="$2"
            delete_webhook "$webhook_id"
            ;;
        test)
            local webhook_id="$2"
            test_webhook "$webhook_id"
            ;;
        update-url)
            local webhook_id="$2"
            local new_url="$3"
            update_webhook_url "$webhook_id" "$new_url"
            ;;
        *)
            echo -e "\n${BLUE}Webhook Manager Usage:${NC}"
            echo "  $0 list                     - List all webhooks"
            echo "  $0 create [url]             - Create a new webhook (uses ngrok URL if none provided)"
            echo "  $0 delete <webhook_id>      - Delete a webhook"
            echo "  $0 test <webhook_id>        - Send a ping event to test a webhook"
            echo "  $0 update-url <id> [url]    - Update webhook URL (uses ngrok URL if none provided)"
            echo ""
            ;;
    esac
}

# Run main function with all arguments
main "$@"