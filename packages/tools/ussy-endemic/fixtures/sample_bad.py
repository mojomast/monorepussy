# Sample Python file with various anti-patterns
import os
import sys


def process_data(data):
    # No type hints
    try:
        result = data["key"]
    except:  # bare except
        pass  # swallow errors

    try:
        x = data["other"]
    except Exception:  # broad except
        pass

    print(f"Processing {data}")  # print debugging


class GodClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
    def method13(self): pass
    def method14(self): pass
    def method15(self): pass
    def method16(self): pass  # > 15 methods = god class


# Good patterns
import logging
logger = logging.getLogger(__name__)


def typed_function(x: int) -> str:
    return str(x)


class CustomError(Exception):
    pass
