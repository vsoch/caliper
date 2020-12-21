__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from abc import abstractmethod


class ManagerBase:
    """A manager base exists to define standard actions for a manager."""

    name = "base"

    def __init__(self, name=None):
        self.uri = name
        self._specs = []
        self.metadata = None

    @abstractmethod
    def get_package_metadata(self):
        pass

    @property
    def specs(self):
        """Retrieve specs and populate _specs if they don't exist"""
        if not self._specs:
            return self.get_package_metadata()
        return self._specs

    @property
    def package_name(self):
        if self.uri:
            return self.uri.replace("%s:" % self.name, "", 1)

    def __str__(self):
        return "[manager:%s]" % self.name

    def __repr__(self):
        return self.__str__()
