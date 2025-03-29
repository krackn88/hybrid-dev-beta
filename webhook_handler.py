import os
import hmac
import hashlib
import logging
from flask import Flask, request, abort
from github import Github
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get environment variables
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_OWNER = os.getenv('REPO_OWNER', 'krackn88')
REPO_NAME = os.getenv('REPO_NAME', 'hybrid-dev-beta')
BRANCH = os.getenv('BRANCH', 'main')
LOCAL_PATH = os.getenv('LOCAL_PATH', os.path.expanduser("~/hybrid-dev-beta"))
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 5000))
AUTO_COMMIT_INTERVAL = int(os.getenv('AUTO_COMMIT_INTERVAL', 30))  # minutes
AUTO_COMMIT = os.getenv('AUTO_COMMIT', 'true').lower() == 'true'

# Initialize GitHub client
g = Github(GITHUB_TOKEN)
repo = g.get_repo(f'{REPO_OWNER}/{REPO_NAME}')

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('X-Hub-Signature-256') is None:
        abort(403)

    # Verify the webhook signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(signature, request.data, WEBHOOK_SECRET):
        abort(403)

    event = request.headers.get('X-GitHub-Event')
    if event == 'push':
        handle_push_event(request.json)

    return '', 200

def verify_signature(signature, data, secret):
    sha_name, signature = signature.split('=')
    mac = hmac.new(secret.encode(), msg=data, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)

def handle_push_event(payload):
    logger.info('Push event received')
    # Pull the latest changes
    subprocess.run(['git', 'pull', 'origin', BRANCH], cwd=LOCAL_PATH)
    logger.info('Repository updated')

def auto_commit():
    import time
    while True:
        if AUTO_COMMIT:
            subprocess.run(['git', 'add', '.'], cwd=LOCAL_PATH)
            subprocess.run(['git', 'commit', '-m', 'Auto-commit'], cwd=LOCAL_PATH)
            subprocess.run(['git', 'push', 'origin', BRANCH], cwd=LOCAL_PATH)
            logger.info('Auto-commit executed')
        time.sleep(AUTO_COMMIT_INTERVAL * 60)

if __name__ == '__main__':
    from threading import Thread
    if AUTO_COMMIT:
        Thread(target=auto_commit).start()
    app.run(port=WEBHOOK_PORT)