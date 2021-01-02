__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.managers import PypiManager
from caliper.utils.file import read_file, write_file, read_yaml
from caliper.utils.command import CommandRunner
from caliper.logger import logger
from jinja2 import Template
from .workers import Workers

import os
import json
import re
import tempfile


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

        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)


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
        parallel=True,
        show_progress=True,
        func=None,
        force=False,
    ):
        """Once the config is loaded, run the analysis using multiprocessing
        workers.
        """
        # The release filter is a regular expression we use to find the correct
        # platform / architecture
        release_filter = release_filter or ".*manylinux.*x86_64.*"
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

        # Read in the template, populate with each deps version
        template = Template(read_file(self.dockerfile, readlines=False))

        # Prepare arguments to build and test a container for each
        tasks = {}

        # Loop over versions of the library, and Python versions
        for version, releases in all_releases.items():

            # Create a lookup based on Python version
            lookup = {x["python_version"]: x for x in releases}

            for python_version in python_versions:
                name = "%s-%s-%s-python-%s" % (
                    self.name,
                    self.dependency,
                    version,
                    python_version,
                )
                outfile = os.path.join(self.outdir, "%s.json" % name)
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
                logger.show_progress(progress, total, length=35, prefix=prefix)
            else:
                logger.info("Processing task %s" % key)

            results[key] = func(**params)
            progress += 1

        return results


def analysis_task(**kwargs):
    """A shared analysis task for the serial or parallel workers. We will
    read in the Dockerfile template, and generate and run/test a container
    for a particular Python version, etc.
    """
    # Ensure all arguments are provided
    for key in [
        "name",
        "outdir",
        "dependency",
        "outfile",
        "dockerfile",
        "exists",
    ]:
        if key not in kwargs or kwargs.get(key) == None:
            logger.exit("%s is missing or undefined for analysis task." % key)

    dockerfile = kwargs.get("dockerfile")
    outfile = kwargs.get("outfile")
    dependency = kwargs.get("dependency")
    force = kwargs.get("force", False)
    exists = kwargs.get("exists")
    name = kwargs.get("name")
    outdir = kwargs.get("outdir")
    result = {"inputs": kwargs}
    tests = kwargs.get("tests")
    tests = [] if not tests else tests.split("\n")

    # If the output file already exists and force is true, overwrite
    if os.path.exists(outfile) and not force:
        logger.info("%s already exists and force is set to False" % outfile)
        return

    # If it doesn't exist, we wouldn't be able to build it, cut out early
    if not exists:
        result["build_retval"] = 1
        return result

    # Build temporary Dockerfile
    dockerfile_name = "Dockerfile.caliper.%s" % name
    dockerfile_fullpath = os.path.join(tempfile.gettempdir(), dockerfile_name)

    # Write and build temporary Dockerfile, and build the container
    write_file(dockerfile_fullpath, dockerfile)
    container_name = "%s-container:%s" % (dependency, name)
    runner = CommandRunner()
    runner.run_command(
        [
            "docker",
            "build",
            "-f",
            dockerfile_fullpath,
            "-t",
            container_name,
            ".",
        ],
        cwd=outdir,
    )

    # Keep a result for each script
    result["build_retval"] = runner.retval
    if runner.retval != 0:
        return result

    # Get packages installed for each container
    runner.run_command(["docker", "run", container_name, "pip", "freeze"])
    result["requirements.txt"] = runner.output

    # Test basic import of library
    tests = {}

    # Run each test
    for script in tests:
        runner.run_command(["docker", "run", container_name, "python", script])
        tests[script] = {
            "error": runner.error,
            "output": runner.output,
            "retval": runner.retval,
        }
    result["tests"] = tests

    # Save the result to file
    write_file(outfile, json.dumps(result))
