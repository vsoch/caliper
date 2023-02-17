__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2023, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
from distutils.version import StrictVersion

from caliper.logger import logger
from caliper.managers.base import ManagerBase
from caliper.utils.command import do_request


class GitHubManager(ManagerBase):
    """
    Retreive GitHub releases
    """

    name = "github"
    baseurl = "https://api.github.com"

    def _get_headers(self):
        """
        If a GitHub token is found in the environment, use it
        """
        token = os.environ.get("GITHUB_TOKEN")
        headers = {
            "Accept": "application/vnd.github.symmetra-preview+json",
        }
        if token:
            headers["Authorization"] = "token %s" % token
        return headers

    def get_package_metadata(self, name=None):
        """
        Given a package name, retrieve it's metadata from pypi
        """
        name = name or self.package_name
        if not name:
            raise ValueError("A package name is required.")

        # At some point we might need to add pagination
        # url = "%s/repos/%s/releases?per_page=100" % (self.baseurl, name)

        # Currently we are using tags, as non verified releases are not included
        url = "%s/repos/%s/tags?per_page=100" % (self.baseurl, name)
        self.metadata = do_request(url, headers=self._get_headers())

        # Parse metadata into simplified version of spack package schema
        for release in self.metadata:
            # Only include valid versions
            try:
                StrictVersion(release["name"].lstrip("v"))
            except Exception:
                continue

            self._specs.append(
                {
                    "name": name,
                    "version": release["name"],
                    "source": {
                        "filename": release["tarball_url"],
                        "type": "targz",
                    },
                    "hash": None,
                }
            )

        # Must sort by version or won't work
        self._specs = self.sort_specs(self._specs, by="version")
        logger.info("Found %s versions for %s" % (len(self._specs), name))
        return self._specs
