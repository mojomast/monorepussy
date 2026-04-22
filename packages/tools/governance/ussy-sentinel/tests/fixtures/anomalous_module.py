"""Anomalous Python module — patterns that differ from typical codebases."""

# Unusual: direct database access
import sqlite3
import hashlib
import base64
import struct
import mmap
import curses
import tkinter


def VeryBadName(x, y, z, a, b, c, d, e, f, g):
    """Too many args, PascalCase function name, no types."""
    r = 0
    if x:
        if y:
            if z:
                if a:
                    if b:
                        r = c
    return r


def a():
    """Single letter function name."""
    pass


def b(c, d, e, f, g, h, i, j, k, l, m, n, o, p):
    """Many args, single letter name."""
    q = c + d + e + f + g + h + i + j + k + l + m + n + o + p
    return q


class MyClass:
    """Class with no methods."""

    pass


def deeply_nested():
    """Extremely deeply nested function."""
    x = 1
    if True:
        if True:
            if True:
                if True:
                    if True:
                        if True:
                            if True:
                                if True:
                                    x = 2
    return x


def many_loops():
    """Function with many loops."""
    for i in range(10):
        for j in range(10):
            for k in range(10):
                while True:
                    break
