__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from distutils.version import StrictVersion
from abc import abstractmethod


class ManagerBase:
    """A manager base exists to define standard actions for a manager."""

    name = "base"
    export_formats = ["json", "zip", "json-single"]

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

    def sort_specs(self, specs, by="version"):
        """If the tags are out of order, we won't be able to derive"""
        lookup = {x["version"].lstrip("v"): x for x in specs}
        versions = [x[by].lstrip("v") for x in self._specs]
        versions.sort(key=StrictVersion)
        return [lookup[x] for x in versions]
