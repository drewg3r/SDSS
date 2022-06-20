from .kernel import File, Directory, Kernel
from getpass import getpass


def echo(command: list[str], kernel: Kernel, workdir: list[str]):
    if len(command) == 1:
        return 'USAGE: echo <message> [> filename]', workdir
    if len(command) == 2:
        return ' '.join(command[1:]), workdir
    if len(command) > 3:
        try:
            if command[3][0] == '/':
                kernel.write(kernel.parse_path(command[3]), command[1])
            else:
                kernel.write(workdir + [command[3]], command[1])
        except ValueError:
            return 'echo: Invalid argument', workdir
        finally:
            return None, workdir


def cd(command: list[str], kernel, workdir: str):
    print(workdir)
    if len(command) == 1:
        return None, []
    else:
        if command[1][0] == '/':
            try:
                kernel.get_directory_content(command[1])
            except ValueError:
                return 'Invalid path', workdir
            else:
                return None, kernel.parse_path(command[1])
        elif command[1] == '..':
            if len(workdir) == 0:
                return None, []
            else:
                return None, workdir[:-1]
        else:
            new_workdir = workdir + kernel.parse_path(command[1])
            try:
                kernel.get_directory_content(new_workdir)
            except ValueError:
                return 'Invalid path', workdir
            else:
                return None, new_workdir


def ls(command: list[str], kernel, workdir: list):
    files: list = []
    dirs: list = []
    try:
        dir_content = kernel.get_directory_content(workdir)
    except ValueError:
        raise ValueError('Invalid path')
    for obj in dir_content:
        entry = kernel.read(workdir + [obj])
        if isinstance(entry, File):
            files.append(f'{entry.permissions_str}  \t{entry.owner}\t{entry.group}\t{entry.filename}'.expandtabs(12))
        elif isinstance(entry, Directory):
            dirs.append(f'directory  \t\t\t{entry.name}'.expandtabs(12))
    if dirs:
        dirs.append('')
    return f'total {len(dir_content)}\n' + '\n'.join(dirs) + '\n'.join(files), workdir


def cat(command: list[str], kernel, workdir: list):
    if len(command) == 1:
        return 'USAGE: cat <filename>', workdir
    try:
        file = kernel.read(workdir + [command[1]])
        if isinstance(file, Directory):
            return 'cat: You can read only files', workdir
    except ValueError:
        return 'Invalid filename', workdir
    else:
        return file.content if file.content != -1 else 'cat: Access denied', workdir


def touch(command: list[str], kernel: Kernel, workdir: list):
    if len(command) == 1:
        return 'USAGE: touch <filename>', workdir
    try:
        kernel.create_file(workdir, command[1], 640, '')
    except ValueError:
        return 'touch: File already exists', workdir
    return None, workdir


def rm(command: list[str], kernel: Kernel, workdir: list):
    if len(command) == 1:
        return 'USAGE: rm <filename>', workdir
    try:
        kernel.remove_file(workdir + [command[1]])
    except ValueError:
        return 'rm: File does not exists', workdir
    except Exception:
        return 'rm: Access denied', workdir
    return None, workdir


def useradd(command: list[str], kernel: Kernel, workdir: list):
    if len(command) == 1:
        return 'USAGE: useradd <username>', workdir
    try:
        kernel.create_user(command[1])
    except ValueError:
        return 'useradd: User already exists', workdir
    except Exception:
        return 'useradd: Access denied', workdir
    return None, workdir


def passwd(command: list[str], kernel: Kernel, workdir: list):
    if len(command) == 1:
        return 'USAGE: passwd <username>', workdir
    password_match = False
    while not password_match:
        password1 = getpass("Enter new password ")
        password2 = getpass("Retype password ")
        password_match = password1 == password2
        if not password_match:
            print("Passwords don't match")
    try:
        kernel.change_user_password(command[1], password1)
    except ValueError as error:
        return 'passwd: ' + str(error), workdir
    # except Exception:
    #     return 'passwd: Access denied', workdir
    return None, workdir


def usermod(command: list[str], kernel: Kernel, workdir: list):
    if len(command) < 4:
        return 'USAGE: usermod <flag> <group> <username>', workdir
    try:
        # -a append
        if command[1] == "-a":
            kernel.add_user_group(username=command[3], group=command[2])
        # -r remove
        if command[1] == "-r":
            kernel.remove_user_group(username=command[3], group=command[2])
    except ValueError as error:
        return 'usermod: ' + str(error), workdir
    except Exception:
        return 'usermod: Access denied', workdir
    return None, workdir


commands = {
    'echo': echo,
    'ls': ls,
    'cat': cat,
    'cd': cd,
    'rm': rm,
    'touch': touch,
    'useradd': useradd,
    'passwd': passwd,
    'usermod': usermod
}
