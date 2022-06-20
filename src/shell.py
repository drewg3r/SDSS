from src.commands import commands as shell_commands
from src.kernel import Kernel
from src.auth import auth
from src.variant_options import wrong_login_amount


class Shell:
    def __init__(self, kernel: Kernel):
        self.kernel: Kernel = kernel
        self.workdir: list = []
        self.active = True

        try:
            self.authentication()
        except Exception:
            self.authentication()

    def authentication(self):
        authenticated = False
        failed_attempts = 1
        user = None
        while not authenticated and failed_attempts < wrong_login_amount:
            try:
                authenticated, input_username = auth(self.kernel)
                if not authenticated and user == input_username:
                    failed_attempts += 1
                user = input_username
            except Exception as e:
                print("authentication error: {}".format(str(e)))

        if not authenticated:
            print("Too many wrong attempts, register again")
            print("Too many wrong attempts, register again")
            self.kernel.remove_user(user)
            raise Exception("Failed to login")


    def prompt(self):
        return f'[{self.kernel.username}] /{"/".join(self.workdir)}> '

    def exec(self, command: str):
        command = command.split()
        if not command:
            return
        if command[0] == 'exit':
            self.active = False
            return 'exit'
        try:
            result, self.workdir = shell_commands[command[0]](command, self.kernel, self.workdir)
            return result
        except KeyError:
            return f'shell: command not found: {command[0]}'
