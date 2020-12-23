__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics.base import MetricFinder
from caliper.managers import GitManager
from caliper.utils.file import write_json, mkdir_p
from caliper.utils.prompt import confirm
from caliper.utils.command import wget_and_extract
from caliper.logger import logger

import importlib
import shutil
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

    def __init__(self, manager=None, working_dir=None, quiet=False):
        self._metrics = {}
        self._extractors = {}
        self.manager = manager
        self.tmpdir = None
        self.git = None
        self.quiet = quiet

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

    def cleanup(self, force=False):
        """Delete a git directory. If force is not set, ask for confirmation"""
        if self.tmpdir and os.path.exists(self.tmpdir):
            if not force and not confirm(
                "Are you sure you want to delete %s?" % self.tmpdir
            ):
                return
        shutil.rmtree(self.tmpdir)

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
        metric = self.get_metric(name)
        metric.extract()
        self._extractors[metric_name] = metric

    def get_metric(self, name):
        """Return a metric object based on name"""
        module, metric_name = self._metrics[name].rsplit(".", 1)
        return getattr(importlib.import_module(module), metric_name)(self.git)

    def prepare_repository(self):
        """Since most source code archives won't include the git history,
        we would want to create a root directly with a new git installation,
        and then create tagged commits that correpond to each version. We
        can then use this git repository to derive metrics of change.
        """
        if not self.manager:
            logger.exit("A manager is required to prepare a repository.")

        # Create temporary git directory
        self.tmpdir = tempfile.mkdtemp(
            prefix="%s-" % self.manager.uri.replace("/", "-")
        )
        self.git = GitManager(self.tmpdir, quiet=self.quiet)

        # Initialize empty respository
        self.git.init()

        # For each version, download and create git commit and tag
        for i, spec in enumerate(self.manager.specs):
            logger.info(
                "Downloading and tagging %s, %s of %s"
                % (spec["version"], i + 1, len(self.manager.specs))
            )
            download_to = os.path.join(
                self.tmpdir, os.path.basename(spec["source"]["filename"])
            )

            # Extraction type is based on source type
            wget_and_extract(
                url=spec["source"]["filename"],
                download_type=spec["source"]["type"],
                download_to=download_to,
            )

            # git add all content in folder, commit and tag with version
            self.git.add()
            self.git.status()
            os.listdir(self.tmpdir)
            self.git.commit(spec["version"])
            self.git.tag(spec["version"])

        logger.info("Repository for %s is created at %s" % (self.manager, self.tmpdir))
        return self.git

    def save_all(self, outdir, force=False):
        """Save data as json exports using an outdir root."""
        if not self.manager or not self._extractors:
            logger.exit("You must add a manager and do an extract() before save.")

        package_dir = os.path.join(outdir, self.manager.name, self.manager.uri)

        written = True
        for _, extractor in self._extractors.items():
            extractor_dir = os.path.join(package_dir, extractor.name)
            mkdir_p(extractor_dir)

            # Prepare to write results to file
            outfile = os.path.join(extractor_dir, "%s-results.json" % extractor.name)
            if os.path.exists(outfile) and not force:
                logger.warning("%s exists and force is False, skipping." % outfile)
                continue

            written = True
            results = extractor.get_results()
            write_json(results, outfile)

        if written:
            logger.info("Results written to %s" % outdir)
