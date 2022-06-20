from getpass import getpass
import random

from src.kernel import Kernel


def __get_control_questions(kernel: Kernel) -> dict:
    questions = kernel.read("/admin/control_questions").content.split("\n")
    questions_dict = dict()
    for i in range(len(questions)):
        questions_dict[i + 1] = questions[i]
    return questions_dict


def __get_random_control_questions(kernel: Kernel) -> dict:
    questions_dict = __get_control_questions(kernel)
    return dict((i, questions_dict[i]) for i in random.sample(range(1, len(questions_dict) + 1), 3))


def registrate(kernel: Kernel, username: str):
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
            questions = __get_random_control_questions(kernel)
            answers = "q:\n"
            for question in questions:
                answers += "\n" + input(questions[question])
        case "2":
            print("Function is: exp(a*x)")
            a = input("Input a: ")
            return "f:\n" + a
