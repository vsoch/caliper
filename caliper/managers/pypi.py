__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.utils.command import do_request
from caliper.logger import logger
from caliper.managers.base import ManagerBase


class PypiManager(ManagerBase):
    """Retreive Pypi package metadata."""

    name = "pypi"
    baseurl = "https://pypi.python.org/pypi"

    def __init__(self, name=None):
        self.uri = name
        self._specs = []
        self.metadata = None

    @property
    def name(self):
        if self.uri:
            return self.uri.replace("pypi:", "", 1)

    @property
    def specs(self):
        """Retrieve specs and populate _specs if they don't exist"""
        if not self._specs:
            return self.get_package_metadata()
        return self._specs

    def get_package_metadata(self, name=None):
        """Given a package name, retrieve it's metadata from pypi"""
        name = name or self.name
        if not name:
            raise ValueError("A package name is required.")

        url = "%s/%s/json" % (self.baseurl, name)
        self.metadata = do_request(url)

        # Parse metadata into simplified version of spack package schema
        for version, release in self.metadata.get("releases", {}).items():
            self._specs.append(
                {
                    "name": self.name,
                    "version": version,
                    "source": {
                        "filename": release[0]["url"],
                        "type": release[0].get("python_version", "source"),
                    },
                    "hash": release[0]["digests"]["sha256"],
                }
            )

        logger.info("Found %s versions for %s" % (len(self._specs), self.name))
        return self._specs
