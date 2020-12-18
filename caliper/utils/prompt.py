__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"


def confirm(prompt, response=False):
    """Used to prompt the user for a yes or no response, and returns True/False.
    This means we can use it like:
    if confirm("Would you like to do the thing?"):
       ....
    """
    prompt = "%s [%s]|%s: " % (prompt, "n", "y")
    while True:
        answer = input(prompt)
        if not answer:
            return response
        if answer not in ["y", "Y", "n", "N"]:
            print("Please respond with y or n.")
            continue
        if answer == "y" or answer == "Y":
            return True
        if answer == "n" or answer == "N":
            return False
