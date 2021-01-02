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

    def do_metadata_request(self, name=None):
        """A separate, shared function to retrieve package metadata without
        doing any custom filtering.
        """
        name = name or self.package_name
        if not name:
            raise ValueError("A package name is required.")

        url = "%s/%s/json" % (self.baseurl, name)
        self.metadata = do_request(url)

    @property
    def releases(self):
        if not self.metadata:
            self.do_metadata_request()
        return self.metadata.get("releases", {})

    def get_package_metadata(self, name=None, arch=None, python_version=None):
        """Given a package name, retrieve it's metadata from pypi. Given an arch
        regex and python version, we look for a particular architecture. Otherwise
        the choices are a bit random.
        """
        # Note that without specifying an arch and python version, the
        # architecture returned can be fairly random.

        # Parse metadata into simplified version of spack package schema
        for version, releases in self.releases.items():

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

    def get_python_versions(self):
        """Given a list of releases (or the default) return a list of pep
        Python versions (e.g., cp38)
        """
        python_versions = set()
        for version, releases in self.releases.items():
            [
                python_versions.add(r["python_version"])
                for r in releases
                if r["python_version"]
            ]
        return python_versions

    def find_release(self, releases=None, arch=None, python_version=None):
        """Given a list of releases, find one that we can extract"""
        filename = None
        releases = releases or self.releases

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

    def filter_releases(self, regex, search_field="filename"):
        """Given a regular expression, filter releases down to smaller list"""
        filtered = {}
        for version, releases in self.releases.items():
            filtered[version] = [
                r for r in releases if re.search(regex, r.get(search_field, ""))
            ]
        return filtered
