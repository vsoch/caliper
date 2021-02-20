__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.logger import logger
from caliper.managers.base import ManagerBase

import os


class DataverseManager(ManagerBase):
    """Retreive Dataverse package metadata."""

    name = "dataverse"
    client = None

    def init_client(self, baseurl="https://dataverse.harvard.edu/"):
        """initialize a dataverse client. We default to the Harvard dataverse,
        and can also retrieve a different url from the environment.
        """
        # If we've already instantiated a client, return
        if self.client:
            return self.client

        try:
            from pyDataverse.api import Api
        except:
            logger.exit("pydataverse is required to use the dataverse manager.")

        # Arguments for the manager come from the environment
        baseurl = os.environ.get("CALIPER_DATAVERSE_BASEURL", baseurl)

        # Create a client for the API
        self.client = Api(baseurl)

    def get_package_metadata(self, name=None):
        """Given a dataset DOI, retrieve it from a dataverse install. Since
        we only retrieve one version, this manager typically only includes
        one set of files corresponding to the latest version.
        """
        name = name or self.package_name
        if not name:
            raise ValueError("A package name is required.")

        # Initialize a client
        self.init_client()

        response = self.client.get_dataset(name)
        if response.status_code != 200:
            logger.exit(
                "Request failed to get %s: %s, %s"
                % (name, response.status_code, response.reason)
            )

        dataset = response.json()

        # Since this corresponds only to the latest version, put into one entry
        files_list = dataset["data"]["latestVersion"]["files"]
        self._specs.append(
            {
                "name": name,
                "version": str(dataset["data"]["latestVersion"]["versionNumber"]),
                "source": {
                    "files": files_list,
                    "type": "source",
                },
                # Note that this isn't a hash, but a unique identifier
                "hash": dataset["data"]["identifier"],
            }
        )
        return self._specs

    def download(self, spec, dest):
        """dataverse specs typically only provide the latest version, and a
        listing of files instead of a single archive.
        """
        # Initialize a client
        self.init_client()

        for fileObject in spec["source"]["files"]:
            download_to = os.path.join(dest, fileObject["dataFile"]["filename"])
            file_id = fileObject["dataFile"]["id"]
            response = self.client.get_datafile(file_id)
            with open(download_to, "wb") as f:
                f.write(response.content)
