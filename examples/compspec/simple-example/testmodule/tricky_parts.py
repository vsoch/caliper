import pandas as pd

# log that we have a global symbol
GLOBAL_SYMBOL = {"I": "AM", "A": "DICTIONARY"}


def free_function():
    print("free function")


def free_function_uses_pandas():
    df = pd.DataFrame()
    df["a"] = [1, 2, 3]
    df.ix(0, 0)


def free_function_uses_arg(
    arg,
):  # would like to get the number of possible arguments that this function can take and type information if available
    arg.text = "A"
    arg.func()


def other_function():
    print("other function")
    b = A()
    free_function(
        b
    )  # can we log that this calls `free_function` with an instance of A?


class A:
    def __init__(self):
        self.text = "A"
        self.func = free_function  # can we understand that this uses free_function()?

    def func():
        print("A")

    def func2(a):
        a.text = "A"
        l = a.func()  # cann we understand that this uses a.func()?

    def func3(a):
        df = pd.DataFrame()  # can we understand that this uses pd.DataFrame()?
        df["a"] = [1, 2, 3]
        a.ix(0, 0)  # can we understand that this uses a.ix()?

    def func4(a):
        df = pd.DataFrame()


def cast_to_A(fun):
    def ret_fun(*args, **kwargs):
        # do stuff here, for eg.
        return fun(A(*args, **kwargs))

    return ret_fun


@cast_to_A
def foo(argument1):  # can we check that this is called with an instance of A?
    assert isinstance(argument1, A)


foo("test")
