__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.managers.base import ManagerBase
from caliper.managers import GitManager
from caliper.utils.command import wget_and_extract
from caliper.logger import logger
import tempfile
import os


class MetricsExtractor:
    """A Metrics Extractor should be used alongside a manager. The manager
    is required to be provided on init, and should provide a list of specs
    in a simplified format of the spack package schema:

      [{'name': 'sregistry-cli',
        'version': '0.2.36',
        'source': {'filename': '.../sregistry-0.2.36.tar.gz',
                   'type': 'source'},
         'hash': '238ebd3ca0e0408e0be6780d45deca79583ce99aed05ac6981da7a2...'}]

    The source should be a url we can download with wget or similar.
    """

    def __init__(self, manager):
        self.manager = manager
        self.tmpdir = None
        self.git = None
        if not isinstance(self.manager, ManagerBase):
            raise ValueError("You must provide a caliper.manager subclass.")

    def prepare_repository(self):
        """Since most source code archives won't include the git history,
        we would want to create a root directly with a new git installation,
        and then create tagged commits that correpond to each version. We
        can then use this git repository to derive metrics of change.
        """
        # Create temporary git directory
        self.tmpdir = tempfile.mkdtemp(prefix="%s-" % self.manager.name)
        self.git = GitManager(self.tmpdir)

        # Initialize empty respository
        self.git.init()

        # For each version, download and create git commit and tag
        for spec in self.manager.specs:
            download_to = os.path.join(
                self.tmpdir, os.path.basename(spec["source"]["filename"])
            )
            wget_and_extract(spec["source"]["filename"], download_to)

            # git add all content in folder, commit and tag with version
            self.git.add()
            self.git.commit(spec["version"])
            self.git.tag(spec["version"])

        logger.info("Repository for %s is created at %s" % (self.manager, self.tmpdir))
        return self.git

        # - dependencies (imports) and requirements.txt
        # - make sure these functions are imported from metrics
        # extract subsequent, figure out git commands to get changes

        # number of changed lines
        # number of changed files
        # new dependencies


def changed_lines(before, after):
    """given a file before and after, count the number of changed lines"""
    # TODO, should be able to do this with git?
    pass
