__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics import MetricsExtractor
from caliper.managers import get_named_manager
from caliper.logger import logger
import os


def main(args, extra):

    # Ensure that all metrics are valid
    client = MetricsExtractor(quiet=True)
    metrics = args.metric.split(",")

    # If asking for all, we will do all regardless of other specifications
    if "all" in metrics:
        metrics = ["all"]

    for metric in metrics:
        if metric == "all":
            continue
        if metric not in client.metrics:
            logger.exit("%s is not a known metric." % metric)

    # prepare top level output directory
    outdir = args.outdir or os.getcwd()

    # Now parse the package names and do the extraction!
    for package in args.packages:
        uri, package = package.split(":")  # pypi:sif
        try:
            manager = get_named_manager(uri, package)
        except NotImplementedError:
            logger.exit("%s is not a valid package manager uri." % package)

        # Create a client to interact with
        client = MetricsExtractor(manager, quiet=True)

        # Honor the args.version
        versions = args.versions.split(",") if args.versions else None

        # Do the extraction
        for metric in metrics:
            if metric == "all":
                client.extract_all(versions=versions)
            else:
                client.extract_metric(metric, versions=versions)

        # Save results to files
        client.save_all(outdir, force=args.force, fmt=args.fmt)

        # Cleanup, unless disabled
        if not args.no_cleanup:
            client.cleanup(force=True)
