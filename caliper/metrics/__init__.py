__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics.base import MetricFinder
from caliper.managers import GitManager
from caliper.utils.file import (
    zip_from_string,
    read_json,
    read_zip,
)
from caliper.utils.prompt import confirm
from caliper.utils.command import wget_and_extract
from caliper.logger import logger

import importlib
import json
import requests
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

    def load_metric(
        self,
        metric,
        filename=None,
        repository="vsoch/caliper-metrics",
        subfolder="",
        branch="main",
        extension="json",
    ):
        """Load a metric from from a file or GitHub repo that has them extracted,
        optionally specifying a custom repository and subfolder. Smaller metrics
        are typically provided via json, and larger ones via zip.
        """
        # A manager is required
        if not self.manager:
            logger.exit("A manager is required to load a metric for.")

        if filename:
            return self._load_metric_file(filename, metric)
        return self._load_metric_repo(metric, repository, subfolder, branch, extension)

    def _load_metric_file(self, filename, metric):
        """helper function to load a metric from a filename. If it's zipped,
        we need to read and decompress.
        """
        name = "%s-results.json" % metric
        if filename.endswith("zip"):
            return json.loads(read_zip(filename, name))
        return read_json(name)

    def _load_metric_repo(self, metric, repository, subfolder, branch, extension):
        """helper function to load a metric from a repository."""
        # If we have a subfolder, add // around it
        if subfolder:
            subfolder = "%s/" % subfolder.strip("/")
        manager = self.manager.replace(":", "/")

        # Load the index for the metric, must exist for all output types
        url = "https://raw.githubusercontent.com/%s/%s/%s%s/%s/index.json" % (
            repository,
            branch,
            subfolder,
            manager,
            metric,
        )

        logger.info("Downloading %s" % url)
        response = requests.get(url)
        if response.status_code == 200:
            index = response.json()
            data = index.get('data', {}) 

            # If the extension is json, prefer single file first
            if extension == "json" and "json-single" in data:
                url = "%s/%s" %(os.path.dirname(url), data['json-single']['url'])
                response = requests.get(url)
                if response.status_code == 200:
                    return response.json()

            elif extension == "zip" and "zip" in data:
                response = requests.get(url, stream=True)
                data = zip_from_string(response.content, filename="%s-results.json" % metric)
                return json.loads(data)

            elif extension == "json" and "json" in data:
                results = {}
                for filename in data["json"].get('urls', []):
                    url = "%s/%s" %(os.path.dirname(url), filename)
                    response = requests.get(url)
                    if response.status_code == 200:
                        results.update(response.json())
                return results
 

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

    def save_all(self, outdir, force=False, fmt=None):
        """Save data as json or zip exports using an outdir root. If fmt is None,
        we use the extractor default (typically single-json except for metrics
        that warrant larger / more extraction).
        """
        if not self.manager or not self._extractors:
            logger.exit("You must add a manager and do an extract() before save.")

        if fmt and fmt not in self.manager.export_formats:
            logger.exit(
                "Export format %s is not recognized. Choose %s."
                % (fmt, ", ".join(self.manager.export_formats))
            )
        package_dir = os.path.join(outdir, self.manager.name, self.manager.uri)
        logger.info("Results will be written to %s" % package_dir)

        for _, extractor in self._extractors.items():

            # Each metric can define a default format
            fmt_ = fmt or extractor.extractor

            # Do save based on selected type
            if fmt_ == "json-single":
                extractor.save_json_single(package_dir, force=force)
            elif fmt_ == "zip":
                extractor.save_zip(package_dir, force=force)
            else:
                extractor.save_json(package_dir, force=force)
