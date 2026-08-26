import logging


class Agent:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    RESET = "\033[0m"

    name: str = "Agent"
    color: str = WHITE

    def log(self, message: str) -> None:
        logging.info("%s[%s] %s%s", self.color, self.name, message, self.RESET)
