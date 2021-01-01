__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.utils.command import do_request
from caliper.logger import logger
from caliper.managers.base import ManagerBase

import re


class PypiManager(ManagerBase):
    """Retreive Pypi package metadata."""

    name = "pypi"
    baseurl = "https://pypi.python.org/pypi"

    def get_package_metadata(self, name=None, arch=None, python_version=None):
        """Given a package name, retrieve it's metadata from pypi. Given an arch
        regex and python version, we look for a particular architecture. Otherwise
        the choices are a bit random.
        """
        name = name or self.package_name
        if not name:
            raise ValueError("A package name is required.")

        url = "%s/%s/json" % (self.baseurl, name)
        self.metadata = do_request(url)

        # Note that without specifying an arch and python version, the
        # architecture returned can be fairly random.

        # Parse metadata into simplified version of spack package schema
        for version, releases in self.metadata.get("releases", {}).items():

            # Find an appropriate linux/unix flavor release to extract
            release = self.find_release(releases, arch, python_version)

            # Some releases can be empty, skip
            if not releases or not release:
                continue

            # Release type drives the extraction logic
            release_type = "wheel" if release["url"].endswith("whl") else "targz"
            self._specs.append(
                {
                    "name": name,
                    "version": version,
                    "source": {
                        "filename": release["url"],
                        "type": release_type,
                    },
                    "hash": release["digests"]["sha256"],
                }
            )

        # Pypi is already sorted by version (at least it seems)
        logger.info("Found %s versions for %s" % (len(self._specs), name))
        return self._specs

    def find_release(self, releases, arch=None, python_version=None):
        """Given a list of releases, find one that we can extract"""
        filename = None

        if arch:
            releases = [r for r in releases if re.search(arch, r["filename"])]
        if python_version:
            releases = [
                r for r in releases if re.search("cp%s" % python_version, r["filename"])
            ]

        for release in releases:
            if re.search("(tar[.]gz|[.]whl)", release["url"]):
                filename = release
        return filename
