import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define roles and permissions
roles_permissions = {
    'admin': ['approve_action', 'configure_settings', 'view_logs', 'emergency_stop'],
    'user': ['view_logs']
}

# User roles
user_roles = {
    'admin_user': 'admin',
    'regular_user': 'user'
}

def has_permission(user, permission):
    role = user_roles.get(user)
    if not role:
        logging.error(f"User {user} does not have a role assigned.")
        audit_log(user, f"Attempted to access {permission} without a role")
        return False
    
    permissions = roles_permissions.get(role, [])
    if permission in permissions:
        logging.info(f"User {user} has permission {permission}.")
        audit_log(user, f"Accessed {permission}")
        return True
    else:
        logging.info(f"User {user} does not have permission {permission}.")
        audit_log(user, f"Attempted to access {permission} without permission")
        return False

def audit_log(user, action):
    with open("audit_log.txt", "a") as log_file:
        log_file.write(f"{user}: {action}\n")
