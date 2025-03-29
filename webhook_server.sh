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
