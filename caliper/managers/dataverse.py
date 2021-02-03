__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.utils.command import do_request
from caliper.logger import logger
from caliper.managers.base import ManagerBase

from copy import deepcopy
import re
import os


class DataverseManager(ManagerBase):
    """Retreive Dataverse package metadata."""

    name = "dataverse"

    def get_package_metadata(self, name=None):
        """Given a package name, retrieve it's metadata from pypi. Given an arch
        regex and python version, we look for a particular architecture. Otherwise
        the choices are a bit random.
        """
        name = name or self.package_name
        if not name:
            raise ValueError("A package name is required.")

        try:
            from pyDataverse.api import Api
            from pyDataverse.models import Dataverse
        except:
            logger.exit("pydataverse is required to use the dataverse manager.")

        # Arguments for the manager come from the environment
        baseurl = os.environ.get(
            "CALIPER_DATAVERSE_BASEURL", "https://dataverse.harvard.edu/"
        )

        # Create a client for the API
        client = Api(baseurl)

        # this one downloads the dataset
        # api.get_dataset(DOI)

        self.metadata = self._specs

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
