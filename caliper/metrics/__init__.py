__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics.base import MetricFinder
from caliper.managers import GitManager
from caliper.utils.command import wget_and_extract
from caliper.logger import logger

import importlib
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

    def __init__(self, manager=None, working_dir=None):
        self._metrics = {}
        self._extractors = {}
        self.manager = manager
        self.tmpdir = None
        self.git = None

        # If we have a working directory provided, the repository exists
        if working_dir:
            self.tmpdir = working_dir
            self.git = GitManager(self.tmpdir)

    def __iter__(self):
        for name, result in self._extractors.items():
            yield name, result

    @property
    def metrics(self):
        """return a list of metrics available"""
        if not self._metrics:
            self._metrics_finder = MetricFinder()
            self._metrics = dict(self._metrics_finder.items())
        return self._metrics

    def extract_all(self):
        for name in self.metrics:
            self.extract_metric(name)

    def extract_metric(self, name):
        """Given a metric, extract for each commit from the repository."""
        if name not in self.metrics:
            logger.exit("Metric %s is not known." % name)

        # If no git repository defined, prepare one
        if not self.git:
            self.prepare_repository()

        module, metric_name = self._metrics[name].rsplit(".", 1)
        metric = getattr(importlib.import_module(module), metric_name)(self.git)
        metric.extract()
        self._extractors[metric_name] = metric

    def prepare_repository(self):
        """Since most source code archives won't include the git history,
        we would want to create a root directly with a new git installation,
        and then create tagged commits that correpond to each version. We
        can then use this git repository to derive metrics of change.
        """
        if not self.manager:
            logger.exit("A manager is required to prepare a repository.")

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
