__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.utils.file import write_file, write_json
from caliper.utils.command import CommandRunner
from caliper.logger import logger

import multiprocessing
import os
import sys
import tempfile
import time


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
    cleanup = kwargs.get("cleanup", False)
    dependency = kwargs.get("dependency")
    force = kwargs.get("force", False)
    exists = kwargs.get("exists")
    name = kwargs.get("name")
    outdir = kwargs.get("outdir")
    result = {"inputs": kwargs}
    tests = kwargs.get("tests")
    tests = [] if not tests else tests.split("\n")
    worker_id = multiprocessing.current_process().name

    # If the output file already exists and force is true, overwrite
    if os.path.exists(outfile) and not force:
        return

    # If it doesn't exist, we wouldn't be able to build it, cut out early
    if not exists:
        result["build_retval"] = 1
        write_json(result, outfile)
        return

    # Build temporary Dockerfile
    dockerfile_name = "Dockerfile.caliper.%s" % name
    dockerfile_fullpath = os.path.join(tempfile.gettempdir(), dockerfile_name)

    # Write and build temporary Dockerfile, and build the container
    write_file(dockerfile_fullpath, dockerfile)
    container_name = "%s-container:%s" % (dependency, name)
    sys.stdout.write(
        "[%s] 0 of %s - building container %s\n"
        % (worker_id, len(tests), container_name)
    )
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

    # Clean up Dockerfile
    if os.path.exists(dockerfile_fullpath):
        os.remove(dockerfile_fullpath)

    # Keep a result for each script
    result["tests"] = {"build": {"retval": runner.retval}}
    if runner.retval != 0:
        result["tests"]["build"]["error"] = runner.error
        write_json(result, outfile)
        return

    # Get packages installed for each container
    runner.run_command(["docker", "run", container_name, "pip", "freeze"])
    result["requirements.txt"] = runner.output

    # Test basic import of library
    test_results = {}

    # Run each test
    for i, script in enumerate(tests):
        start = time.time()
        sys.stdout.write("[%s] %s of %s - %s" % (worker_id, i + 1, len(tests), script))
        runner.run_command(["docker", "run", "--rm", container_name, "python", script])
        end = time.time()
        test_results[script] = {
            "error": runner.error,
            "output": runner.output,
            "retval": runner.retval,
            "seconds": round(end - start, 2),
        }
        sys.stdout.write(" total time: %s seconds \n" % test_results[script]["seconds"])
        sys.stdout.flush()

    # Update results with all tests
    result["tests"].update(test_results)

    # Save the result to file, clean up
    write_json(result, outfile)
    runner.run_command(["docker", "rmi", container_name, "--force"])
    runner.run_command(["docker", "images", "-f", "dangling=true", "-q"])
    for layer in runner.output:
        runner.run_command(["docker", "rmi", layer.strip("\n"), "--force"])
    if cleanup:
        runner.run_command(["docker", "system", "prune", "--all", "--force"])
