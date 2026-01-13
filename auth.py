from config import get_admin_credentials

def check_login(username, password):
    admin_user, admin_pw = get_admin_credentials()
    return username == admin_user and password == admin_pw
