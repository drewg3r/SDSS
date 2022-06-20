import json
import datetime
from getpass import getpass
import random

import src.variant_options


class File:
    def __init__(self, filename: str, path: str, owner: str, group: str,
                 permissions: int, content: str | bool, *args, **kwargs):
        self.filename: str = filename
        self.path: str = path
        self.owner: str = owner
        self.group: str = group
        self.permissions: int = permissions
        self.content: str | int = content

    @property
    def permissions_str(self):
        octal = str(self.permissions)
        while len(octal) < 3:
            octal = '0' + octal

        if len(octal) > 3:
            octal = octal[-3:]
        result = ''
        value_letters = [(4, 'r'), (2, 'w'), (1, 'x')]
        for digit in [int(n) for n in str(octal)]:
            for value, letter in value_letters:
                if digit >= value:
                    result += letter
                    digit -= value
                else:
                    result += '-'
        return result

    def __str__(self):
        return f'File {self.path}{"/" if self.path != "/" else ""}{self.filename}:\n' \
               f'OWNER:GROUP = {self.owner}:{self.group}\n' \
               f'Permissions: {self.permissions}\n' \
               f'---\n' \
               f'{self.content if self.content != -1 else "Access denied"}\n'

    @classmethod
    def from_dict(cls, filename: str, path: str, file: dict):
        return cls(filename, path, **file)


class Directory:
    def __init__(self, path: str):
        self.path: str = path

    @property
    def name(self):
        return self.path.split('/')[-1]

    def __str__(self):
        return f'Directory {self.path}'


class Kernel:

    def __init__(self, partition_path: str, username: str, groups: list[str]):
        self.username: str = username
        self.groups: list[str] = groups
        self.partition_path: str = partition_path
        with open(partition_path) as partition_json:
            self.partition: dict = json.load(partition_json)

    def set_user(self, username: str):
        self.username: str = username
        self.groups: list[str] = self.__get_user_data(username)["groups"]

    @classmethod
    def parse_path(cls, path: str):
        if isinstance(path, list):
            return path
        path = path.split('/')
        path = list(filter(None, path))  # Remove empty elements
        return path

    def __get_filesystem_entry(self, path: str | list[str]) -> dict:
        if isinstance(path, str):
            path = self.parse_path(path)
        entry = self.partition['filesystem']['root']['content']
        try:
            if len(path) == 0:
                return self.partition['filesystem']['root']
            if len(path) == 1:
                return entry[path[0]]
            for path_part in path[:-1]:
                entry = entry[path_part]['content']
            else:
                entry = entry[path[-1]]
        except KeyError:
            raise ValueError(f'Invalid path: {"/"+"/".join(path)}')
        return entry

    def __get_file(self, path: str | list) -> File:
        if isinstance(path, str):
            path = self.parse_path(path)
        file = self.__get_filesystem_entry(path)
        return File.from_dict(path[-1], f'/{"/".join(path[:-1])}', file)

    def __get_directory(self, path: str | list) -> Directory:
        if isinstance(path, str):
            path = self.parse_path(path)
        return Directory(f'/{"/".join(path)}')

    def get_directory_content(self, path: str | list) -> tuple[str]:
        entry = self.__get_filesystem_entry(path)
        if entry['type'] == 'file':
            raise ValueError(f'This is file')
        return tuple(entry['content'].keys())

    def __check_read_permission(self, path: str | list, username: str, groups: list[str]) -> bool:
        entry = self.__get_filesystem_entry(path)
        if entry['type'] == 'file':
            match entry:
                case entry if entry['owner'] == username:
                    if entry['permissions'] // 100 > 4:
                        return True
                case entry if entry['group'] in groups:
                    if entry['permissions'] // 10 % 10 > 4:
                        return True
                case entry:
                    if entry['permissions'] % 10 > 4:
                        return True
        return False

    def __check_write_permission(self, path: str | list, username: str, groups: list[str]) -> bool:
        entry = self.__get_filesystem_entry(path)
        if entry['type'] == 'file':
            match entry:
                case entry if entry['owner'] == username:
                    if entry['permissions'] // 100 in [2, 3, 6, 7]:
                        return True
                case entry if entry['group'] in groups:
                    if entry['permissions'] // 10 % 10 in [2, 3, 6, 7]:
                        return True
                case entry:
                    if entry['permissions'] % 10 in [2, 3, 6, 7]:
                        return True
        return False

    def __create_directory(self, path: str | list, name: str):
        entry = self.__get_filesystem_entry(path)
        entry['content'][name] = {'type': 'directory', 'content': {}}

    def create_directory(self, path: str | list, name: str):
        entry = self.__get_filesystem_entry(path)
        if name in entry['content'].keys():
            raise ValueError('Directory already exists')
        self.__create_directory(path, name)
        self.flush()

    def __remove_directory(self, path: str | list, name: str):
        entry = self.__get_filesystem_entry(path)
        del entry['content'][name]

    def remove_directory(self, path: str | list):
        if isinstance(path, str):
            path = self.parse_path(path)
        entry = self.__get_filesystem_entry(path)
        if entry['content'].keys():
            raise ValueError('Directory is not empty')
        self.__remove_directory(path[:-1], path[-1])
        self.flush()

    def __create_file(self, path: str | list, name: str, owner: str, group: str, permissions: int, content: str = ''):
        entry = self.__get_filesystem_entry(path)
        entry['content'][name] = {'type': 'file', 'owner': owner,
                                  'group': group, 'permissions': permissions, 'content': content}

    def create_file(self, path: str | list, name: str, permissions: int, content: str = ''):
        entry = self.__get_filesystem_entry(path)
        if name in entry['content'].keys():
            raise ValueError('File already exists')
        if not (name and isinstance(permissions, int)):
            raise ValueError('Invalid file info provided')
        self.__create_file(path, name, self.username, self.groups[0], permissions, content)
        self.flush()

    def __remove_file(self, path: str | list, name: str):
        entry = self.__get_filesystem_entry(path)
        del entry['content'][name]

    def remove_file(self, path: str | list):
        if isinstance(path, str):
            path = self.parse_path(path)
        if not self.__check_write_permission(path, self.username, self.groups):
            raise Exception('Access denied')
        self.__remove_file(path[:-1], path[-1])
        self.flush()

    def __change_file_permissions(self, path: str | list, permissions: int):
        entry = self.__get_filesystem_entry(path)
        entry['permissions'] = permissions

    def change_file_permissions(self, path: str | list, permissions: int):
        entry = self.__get_filesystem_entry(path)
        if entry['owner'] != self.username:
            raise Exception('Access denied')
        self.__change_file_permissions(path, permissions)
        self.flush()

    def __write(self, path: str | list, content: str) -> None:
        entry = self.__get_filesystem_entry(path)
        if entry['type'] != 'file':
            raise ValueError('You can write only to files')
        entry['content'] = content

    def update(self):
        with open(self.partition_path) as partition_json:
            self.partition: dict = json.load(partition_json)

    def flush(self):
        partition_json = json.dumps(self.partition, indent=4)
        with open(self.partition_path, 'w') as partition_file:
            partition_file.write(partition_json)

    def read(self, path: str | list) -> File | Directory:
        entry = self.__get_filesystem_entry(path)
        if entry['type'] == 'file':
            file: File = self.__get_file(path)
            if not self.__check_read_permission(path, self.username, self.groups):
                file.content = -1
            return file
        elif entry['type'] == 'directory':
            return self.__get_directory(path)

    def write(self, path: str | list, content: str) -> None:
        try:
            entry = self.__get_filesystem_entry(path)
            if entry['type'] == 'file':
                if self.__check_write_permission(path, self.username, self.groups):
                    self.__write(path, content)
        except ValueError:
            try:
                path = self.parse_path(path)
                self.__get_filesystem_entry(path[:-1])
            except ValueError:
                raise ValueError(f'Invalid path: {path}')
            else:
                self.__create_file(path[:-1], path[-1], self.username,
                                   self.groups[0] if len(self.groups) > 0 else self.username, 640, content)
        self.flush()

    # working with users
    def get_existing_users(self):
        entry = self.__get_filesystem_entry("")['content']['admin']['content']['users']['content']
        return entry

    def create_user(self, username: str):
        if self.username != "root":
            raise Exception('Access denied')
        if username in self.get_existing_users():
            raise ValueError("User already exists")
        if len(self.get_existing_users()) >= src.variant_options.max_users_amount:
            raise Exception("Users limit has been reached")
        else:
            entry = self.__get_filesystem_entry("")['content']['admin']['content']['users']
            self.create_file("/admin/users/", username, 660)

    def remove_user(self, username: str):
        if username not in self.get_existing_users():
            raise ValueError("User don't exist")
        else:
            self.remove_file("/admin/users/" + username)

    def __update_user_data(self, username: str, password: str, groups: tuple | list, confirmation_methods = None):
        path = "/admin/users/" + username
        content = " ".join((username, password, ",".join(groups)))
        if confirmation_methods:
            content = "\n".join((content, confirmation_methods))
        self.write(path, content)

    def __check_password(self, password: str):
        password_min_length = src.variant_options.password_length
        should_contain_letters = 1
        should_contain_numbers = 0
        if len(password) < password_min_length:
            raise ValueError("Password should contain at least {} characters".format(password_min_length))
        if should_contain_numbers and not any(char.isdigit() for char in password):
            raise ValueError("Password should contain numbers".format(password_min_length))
        if should_contain_letters and not any(char.isalpha() for char in password):
            raise ValueError("Password should contain letters".format(password_min_length))

    def change_user_password(self, username: str, password: str):
        if self.username != "root":
            raise Exception("Access denied")
        if username not in self.get_existing_users():
            raise ValueError("User don't exist")
        else:
            self.__check_password(password)
            password += "({})".format(str(datetime.date.today()))
            if not self.read("/admin/users/" + username).content:
                confirmation_methods = self.registrate_confirmation_methods(username)
                self.__update_user_data(username, password, [username], confirmation_methods=confirmation_methods)
                return
            user_data = self.__get_user_data(username)
            confirmation_methods = "\n".join(user_data["confirmation_methods"])
            self.__update_user_data(user_data["username"], password, user_data["groups"], confirmation_methods)

    def __get_user_data(self, username: str):
        path = "/admin/users/" + username
        data = self.__get_file(path).content.split("\n")
        user_data = data.pop(0).split()
        user_groups = user_data[2].split(",")
        return {"username": user_data[0], "password": user_data[1], "groups": user_groups, "confirmation_methods": data}

    def add_user_group(self, username: str, group: str):
        if self.username != "root":
            raise Exception("Access denied")
        if username not in self.get_existing_users():
            raise ValueError("User don't exist")
        else:
            user_data = self.__get_user_data(username)
            user_data["groups"].append(group)
            confirmation_methods = "\n".join(user_data["confirmation_methods"])
            self.__update_user_data(user_data["username"], user_data["password"], user_data["groups"], confirmation_methods)

    def remove_user_group(self, username: str, group: str):
        if self.username != "root":
            raise Exception("Access denied")
        if username not in self.get_existing_users():
            raise ValueError("User don't exist")
        else:
            user_data = self.__get_user_data(username)
            if group in user_data["groups"]:
                user_data["groups"].remove(group)
            else:
                raise ValueError("User is not a part of this group")
            confirmation_methods = "\n".join(user_data["confirmation_methods"])
            self.__update_user_data(user_data["username"], user_data["password"], user_data["groups"], confirmation_methods)

    def get_user_password(self, username: str):
        user_data = self.__get_user_data(username)
        password_string = user_data["password"]
        password = password_string.split("(")[0]
        date = password_string[password_string.find("(")+1 : password_string.find(")")]
        return {"password": password, "creation_date": date}

    def __get_control_questions(self) -> dict:
        questions = self.read("/admin/control_questions").content.split("\n")
        questions_dict = dict()
        for i in range(len(questions)):
            questions_dict[i + 1] = questions[i]
        return questions_dict

    def __get_random_control_questions(self) -> dict:
        questions_dict = self.__get_control_questions()
        return dict((i, questions_dict[i]) for i in random.sample(range(1, len(questions_dict) + 1), 3))

    def registrate_confirmation_methods(self, username: str):
        while True:
            choise = input("Please, select would you prefer to "
                           "1)answer questions or 2)use secret function to confirm your identity\n")
            match choise:
                case "1" | "2":
                    break
                case _:
                    print("Wrong selection, type 1 or 2")

        match choise:
            case "1":
                questions = self.__get_random_control_questions()
                answers = "q:"
                for question in questions:
                    answers += " ".join(("\n", str(question)+":", input(questions[question])))
                return answers
            case "2":
                print("Function is: exp(a*x)")
                a = input("Input a: ")
                return "f:\n" + a

    def confirm_identity(self, username: str):
        print("Please, confirm_your identity")
        confirmation_data = self.__get_user_data(username)["confirmation_methods"]
        confirmation_method = confirmation_data[0][:1]
        match confirmation_method:

            case "f":
                a = int(confirmation_data[1])
                x = random.randint(0, 100)
                # print(round(src.variant_options.secret_function(a, x), 2))  # the answer
                print("Calculate the secret function using given parameters and write the answer (rounded to 2 characters after comma)")
                print("x = {}".format(x))
                attempts_number = 0
                while attempts_number < src.variant_options.wrong_answers_amount:
                    answer = float(input("Answer: "))
                    if answer == round(src.variant_options.secret_function(a, x), 2):
                        return
                    else:
                        print("Wrong!")
                    attempts_number += 1
                raise Exception("User not identified")

            case "q":
                answers = {}
                questions = self.__get_file("/admin/control_questions").content.split("\n")
                for item in confirmation_data[1:]:
                    item = item.split()
                    answers[int(item[0][:1])] = item[1]
                random_question_number = random.choice(tuple(answers.keys()))
                print(questions[random_question_number-1])
                attempts_number = 0
                while attempts_number < src.variant_options.wrong_answers_amount:
                    answer = input("Answer: ")
                    if answer == answers[random_question_number]:
                        return
                    else:
                        print("Wrong!")
                    attempts_number += 1
                raise Exception("User not identified")
