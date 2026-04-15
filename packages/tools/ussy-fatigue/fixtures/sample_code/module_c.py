"""Module C that imports D."""

from .module_d import func_d


def func_c():
    return func_d()
