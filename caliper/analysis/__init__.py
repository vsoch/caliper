__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.managers import PypiManager
from caliper.utils.file import read_file, read_yaml
from caliper.utils.command import CommandRunner
from caliper.logger import logger
from jinja2 import Template
from .workers import Workers
from .tasks import analysis_task

import os
import re


class CaliperAnalyzerBase:
    """A Caliper Analyzer takes a caliper.yaml, reads it in, and then builds
    containers across a grid of builds to test a set of user provided scripts.
    This analyzer base provides the functionality to read in and validate
    the caliper.yaml, and abstract functions for the main classes. Output
    is generated alongside the caliper.yaml in a hidden directory, .caliper.
    """

    name = "base"

    def __init__(self, config_file):
        self._load_config(config_file)

    def __str__(self):
        return "[%s-analyzer:%s]" % (self.name, self.dependency)

    def __repr__(self):
        return self.__str__()

    def _load_config(self, config_file):
        """Given a caliper.yaml file, load the config an ensure that it is valid."""
        if not os.path.exists(config_file):
            logger.exit("%s does not exist." % config_file)
        self.config_file = config_file
        self.config_dir = os.path.abspath(os.path.dirname(self.config_file))
        self.config = read_yaml(config_file).get("analysis", {})
        self.outdir = os.path.join(self.config_dir, ".caliper")
        self.data_dir = os.path.join(self.outdir, "data")

        # Validate that required fields are present, and set
        required = ["packagemanager", "dependency"]
        for key in required:
            if key not in self.config or not self.config.get(key):
                logger.exit(
                    "%s is a required field in the caliper.yaml config under the analysis key."
                    % key
                )

        # Set the Dockerfile, ensure it exists
        self.dockerfile = os.path.join(
            self.config_dir, self.config.get("dockerfile", "Dockerfile")
        )
        if not os.path.exists(self.dockerfile):
            logger.exit("The Dockerfile does not exist.")

        # Set the dependency name and any additional args
        self.dependency = self.config.get("dependency")
        self.args = self.config.get("args", {})

        # Filter to specific python and library versions
        self.python_versions = self.config.get("python_versions", [])
        self.test_versions = self.config.get("versions", [])
        for dirname in [self.outdir, self.data_dir]:
            if not os.path.exists(dirname):
                os.makedirs(dirname)


class CaliperAnalyzer(CaliperAnalyzerBase):
    def get_analyzer(self):
        """Given the validated and loaded config, return the correct analyzer
        class depending on the packagemanger field. Currently we only support
        pypi
        """
        if re.search("pypi", self.config["packagemanager"], re.IGNORECASE):
            return CaliperPypiAnalyzer(self.config_file)
        logger.exit(
            "%s is not a supported package manager at this time."
            % self.config["packagemanager"]
        )


class CaliperPypiAnalyzer(CaliperAnalyzerBase):
    """A Pypi Analyzer expects a package that is intended for pypi."""

    name = "pypi"

    def run_analysis(
        self,
        release_filter=None,
        nproc=None,
        parallel=False,
        show_progress=True,
        func=None,
        force=False,
        cleanup=False,
    ):
        """Once the config is loaded, run the analysis."""
        # The release filter is a regular expression we use to find the correct
        # platform / architecture. We select linux wheels and source
        release_filter = release_filter or "(.*manylinux.*x86_64.*|[.]tar[.]gz)"
        func = func or analysis_task

        # prepare a command runner, check that docker is installed
        runner = CommandRunner()
        runner.run_command(["which", "docker"])
        if runner.retval != 0:
            logger.exit("Docker must be installed to build containers.")

        # Prepare arguments for runner, whether it's serial or parallel
        manager = PypiManager(self.dependency)
        all_releases = manager.filter_releases(release_filter)
        python_versions = manager.get_python_versions()
        python_version_regex = "(%s)" % "|".join(self.python_versions)

        # Read in the template, populate with each deps version
        template = Template(read_file(self.dockerfile, readlines=False))

        # Prepare arguments to build and test a container for each
        tasks = {}

        # Loop over versions of the library, and Python versions
        for version, releases in all_releases.items():

            # Check if the user has defined a set of versions
            if self.test_versions and version not in self.test_versions:
                continue

            # Create a lookup based on Python version
            lookup = {x["python_version"]: x for x in releases}

            for python_version in python_versions:

                # If the user has requested a subset of Python versions
                if self.python_versions and not re.search(
                    python_version_regex, python_version, re.IGNORECASE
                ):
                    continue

                name = "%s-%s-%s-python-%s" % (
                    self.name,
                    self.dependency,
                    version,
                    python_version,
                )
                outfile = os.path.join(self.data_dir, "%s.json" % name)
                spec = lookup.get(python_version, {})
                tests = "\n".join(self.config.get("tests"))

                # If the Python version is not in the lookup we cannot do a build
                exists = python_version in lookup

                # It's easier to pass the rendered template than all arguments for it
                container_base = "python:%s" % ".".join(
                    [x for x in python_version.lstrip("cp")]
                )
                result = template.render(
                    base=container_base,
                    filename=spec.get("url", ""),
                    basename=spec.get("filename", ""),
                    **self.args
                )
                params = {
                    "dependency": self.dependency,
                    "outfile": outfile,
                    "dockerfile": result,
                    "force": force,
                    "exists": exists,
                    "name": name,
                    "tests": tests,
                    "cleanup": cleanup,
                    "outdir": self.config_dir,
                }
                tasks[name] = (func, params)

        if parallel:
            return self._run_parallel(tasks, nproc, show_progress)
        return self._run_serial(tasks)

    def _run_parallel(self, tasks, nproc, show_progress=True):
        """Run tasks in parallel"""
        workers = Workers(nproc, show_progress=show_progress)
        for key, task in tasks.items():
            workers.add_task(key, func=task[0], params=task[1])
        return workers.run()

    def _run_serial(self, tasks, show_progress=True):
        """Run tasks in serial. The workers save result files, so we don't
        care about the results (would take more memory to try and return the
        same content).
        """
        progress = 1
        total = len(tasks)

        results = {}
        for key, task in tasks.items():
            func, params = task
            prefix = "[%s/%s]" % (progress, total)
            if show_progress:
                logger.info("%s: %s" % (prefix, key))
            else:
                logger.info("Processing task %s" % key)

            results[key] = func(**params)
            progress += 1

        return results
