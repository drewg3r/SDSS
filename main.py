from src.kernel import Kernel
from src.shell import Shell

from datetime import datetime, timedelta

kernel = Kernel('disc.json', 'andrew', ['andrew', 'storage', 'admin'])

shell = Shell(kernel)

time_of_user_comfirmation = datetime.now() + timedelta(seconds=20)
while shell.active:
    user_input = input(shell.prompt())
    command_result = shell.exec(user_input)
    if command_result:
        print(command_result)
    if datetime.now() >= time_of_user_comfirmation:
        try:
            kernel.confirm_identity(kernel.username)
        except Exception as error:
            print(str(error))
            print("Identity not confirmed. Logging out...")
            shell.authentication()
        time_of_user_comfirmation = datetime.now() + timedelta(minutes=1)

