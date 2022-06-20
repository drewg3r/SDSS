from math import exp


def secret_function(a: int, x: int):
    return exp(a * x)


password_length = 8
max_users_amount = 5
password_expire_time = 5  # days

wrong_answers_amount = 4
wrong_login_amount = 3
