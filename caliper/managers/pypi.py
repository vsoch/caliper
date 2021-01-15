__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.utils.command import do_request
from caliper.logger import logger
from caliper.managers.base import ManagerBase

from copy import deepcopy
import re


class PypiManager(ManagerBase):
    """Retreive Pypi package metadata."""

    name = "pypi"
    baseurl = "https://pypi.python.org/pypi"
    source_versions = ["cp27", "cp35", "cp38"]

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
    def source_only(self):
        """We care that a package is source only so we know to use artifically
        generated self.source_versions instead. Ideally this matches an install
        to a specific version of Python. We assume one of the following:
        1) that a package is all wheels,
        2) that a package is all source code releases
        3) that a package is a combination of source and wheels
        We don't handle well the case that a package was 1 or 2 and then switches.
        """
        if not hasattr(self, "_source_only"):
            self._source_only = True
            for _, releases in self.releases.items():
                for release in releases:
                    if release["python_version"] != "source":
                        self._source_only = False
                        return self._source_only
        return self._source_only

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
        logger.info(
            "Found %s versions for %s" % (len(self._specs), name or self.package_name)
        )
        return self._specs

    def get_python_versions(self):
        """Given a list of releases (or the default) return a list of pep
        Python versions (e.g., cp38)
        """
        python_versions = set()
        for version, releases in self.releases.items():
            for r in releases:
                if r["python_version"] and r["python_version"] != "source":
                    python_versions.add(r["python_version"])

                # If we have source, we can only test it over a range of versions
                elif (
                    r["python_version"]
                    and r["python_version"] == "source"
                    and self.source_only
                ):
                    [
                        python_versions.add(source_version)
                        for source_version in self.source_versions
                    ]

        return python_versions

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

    def filter_releases(self, regex, search_field="filename", source_versions=None):
        """Given a regular expression, filter releases down to smaller list.
        If a release has version "source" we cannot be sure what version of
        Python to use, so we return a set that ranges between 2.7 and 3.8.
        """
        filtered = {}
        for version, releases in self.releases.items():
            subset = []

            # Only add releases that match regular expression
            for r in releases:
                if re.search(regex, r.get(search_field, "")):

                    # We only added sources if there aren't wheels
                    if r["python_version"] == "source" and self.source_only:
                        for source_version in self.source_versions:
                            rcopy = deepcopy(r)
                            rcopy["python_version"] = source_version
                            subset.append(rcopy)
                    else:
                        subset.append(r)
            filtered[version] = subset
        return filtered
