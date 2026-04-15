"""Module B that imports A — circular!"""

from .module_a import func_a


def func_b():
    return func_a()
