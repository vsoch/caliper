__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2023, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
import re
import shutil
from copy import deepcopy

import requests

from caliper.logger import logger
from caliper.managers.base import ManagerBase
from caliper.utils.command import move_files, wget_and_extract_bz2
from caliper.utils.file import get_tmpdir


class CondaManager(ManagerBase):
    """
    Retreive Conda package metadata.
    """

    name = "conda"

    @property
    def releases(self):
        return self._specs

    def update_repodata(self, name):
        """
        Update repository data, with name <channel>/<subdir>
        """
        url = f"https://conda.anaconda.org/{name}/repodata.json"
        res = requests.get(url, allow_redirects=True)

        # Response status code not 200, no go
        if res.status_code != 200:
            logger.exit(f"Failed to retrieve {url}: {res.json()}")

        # TODO at scale we will want to cache this.
        self._data = res.json()

    @property
    def data(self):
        if hasattr(self, "_data") and self._data:
            return self._data

    def get_package_metadata(self, name=None, arch=None, python_version=None):
        """
        Given a package name, retrieve it's metadata from pypi. Given an arch
        regex and python version, we look for a particular architecture. Otherwise
        the choices are a bit random.
        """
        # Note that without specifying an arch and python version, the
        # architecture returned can be fairly random.
        name = name or self.package_name

        # We should have <channel>/<subdir>/<package>
        # Split the package from the rest
        name, package = name.rsplit("/", 1)
        logger.info(f"Looking for {package} in {name}")

        # Use current repository data
        if not self.data:
            self.update_repodata(name)

        # Look in this order
        found = {}
        for package_type in ["packages.conda", "packages"]:
            found = {
                k: v
                for k, v in self.data.get(package_type, {}).items()
                if v["name"] == package
            }
            if found:
                logger.info(f"Found package {package} in {package_type} repository")
                break

        if not found:
            logger.exit(f"Package {package} is not known to {name}.")

        # Go through releases and add to specs
        for archive, meta in found.items():
            meta["archive"] = archive

            # Assemble the full filename to download
            filename = f"https://conda.anaconda.org/{name}/{archive}"
            meta["source"] = {"filename": filename, "type": "bz2"}
            # Release type drives the extraction logic
            self._specs.append(meta)

        # Pypi is already sorted by version (at least it seems)
        logger.info(f"Found {len(self._specs)} versions for {name}/{package}")
        return self._specs

    def download(self, spec, dest):
        """
        Download a source to a destination.

        Handle the custom structure of the conda extraction
        """
        # Download to temporary location so we can move nested asset into dest
        tmpdir = get_tmpdir()
        download_to = os.path.join(tmpdir, os.path.basename(spec["source"]["filename"]))
        url = spec["source"]["filename"]
        wget_and_extract_bz2(url, download_to, chunk_size=1024)

        # This should be the dest_dir
        dest_dir = os.path.join(tmpdir, "site-packages", spec["name"])
        if not os.path.exists(dest_dir):
            logger.exit(
                f"Unexpected package structure, site-packages missing in {dest_dir}"
            )

        # Extract to the name of the module
        module_dir = os.path.join(dest, spec["name"])
        if not os.path.exists(module_dir):
            os.makedirs(module_dir)
        move_files(dest_dir, module_dir)

        # Remove the archive
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        return dest

    def filter_releases(self, regex, search_field="filename", source_versions=None):
        """Given a regular expression, filter releases down to smaller list.
        If a release has version "source" we cannot be sure what version of
        Python to use, so we return a set that ranges between 2.7 and 3.8.
        """
        print("FILTER VERSIONS")
        import IPython

        IPython.embed()
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
