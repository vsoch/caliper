import math
import re
from typing import Union


def add(A: Union[int, float], B: Union[int, float]) -> Union[int, float]:
    """
    Add two numbers, and an example using typing
    """
    return A + B


def power(A, by=2):
    """
    Return A to the by power, which defaults to 2
    """
    return A**by


def float_power(A, by=2.2):
    """
    A function with the default as a float.
    """
    return A**by


def ceiling(A):
    """
    Get the ceiling.
    """
    return math.ceil(A)


def contains(string, substring):
    """
    A terrible function to wrap re
    """
    return re.search(substring, string) is not None


if __name__ == "__main__":
    print(f"Add 2+4: {add(2,4)}")
    print(f"Power 2^4: {power(2,4)}")
    print(f"Ceiling 2.4: {ceiling(2.4)}")
    print(f"Contains pancakes->pancake: {contains('pancakes', 'pancake')}")
