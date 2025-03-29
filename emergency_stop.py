import logging
from permissions import has_permission

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Emergency stop status
emergency_stopped = False

def emergency_stop(user):
    global emergency_stopped
    if not has_permission(user, 'emergency_stop'):
        logging.error(f"User {user} is not authorized to trigger emergency stop.")
        return False
    
    emergency_stopped = True
    logging.info(f"Emergency stop triggered by {user}.")
    return True

def is_emergency_stopped():
    return emergency_stopped
