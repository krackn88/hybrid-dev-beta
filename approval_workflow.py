import logging
from permissions import has_permission

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Action requests queue
action_requests = []

def request_action(user, action):
    if not has_permission(user, 'approve_action'):
        logging.error(f"User {user} is not authorized to request actions.")
        return False
    
    action_requests.append({'user': user, 'action': action, 'status': 'pending'})
    logging.info(f"Action request for {action} by {user} added to the queue.")
    return True

def approve_action(admin_user, request_index):
    if not has_permission(admin_user, 'approve_action'):
        logging.error(f"User {admin_user} is not authorized to approve actions.")
        return False
    
    if request_index < 0 or request_index >= len(action_requests):
        logging.error("Invalid action request index.")
        return False
    
    action_requests[request_index]['status'] = 'approved'
    logging.info(f"Action request {request_index} approved by {admin_user}.")
    return True

def get_pending_requests():
    return [req for req in action_requests if req['status'] == 'pending']
