"""Custom errors for motor driver."""

from colorama import Fore


class DispenserError(Exception):
    def __init__(self, message):
        self.message = Fore.RED + message
        super().__init__(Fore.RED + self.message)
