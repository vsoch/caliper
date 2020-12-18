__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"


class ManagerBase:
    """A manager base exists to define standard actions for a manager."""

    name = "base"

    def __str__(self):
        return "[manager:%s]" % self.name

    def __repr__(self):
        return self.__str__()
