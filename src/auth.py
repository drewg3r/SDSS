from getpass import getpass
from datetime import datetime, timedelta
import random

from src.kernel import Kernel
from src.variant_options import password_expire_time


def __check_password(kernel: Kernel, username: str, password: str):
    password_data = kernel.get_user_password(username)
    correct_password = password_data["password"]
    password_creation_date = datetime.strptime(password_data["creation_date"], "%Y-%m-%d")
    password_expiration_day = password_creation_date + timedelta(days=password_expire_time)
    if datetime.today() > password_expiration_day:
        raise Exception("Your password expired, set new one")
    else:
        print("Your password will expire {}".format(password_expiration_day))
    if password != correct_password:
        raise ValueError("Wrong password")


def auth(kernel: Kernel):
    username = input("Input your username: ")
    if username not in kernel.get_existing_users():
        raise ValueError("User don't exist")
    password = getpass("Enter your password: ")
    try:
        __check_password(kernel, username, password)
    except ValueError as error:
        print("authentication error: Wrong password")
        return False, username
    kernel.set_user(username)
    return True, username

