__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics import MetricsExtractor
from caliper.managers import get_named_manager
from caliper.utils.file import mkdir_p, write_json
import tempfile
import logging
import os

logger = logging.getLogger("caliper.client")


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
    outdir = args.outdir or tempfile.mkdtemp(prefix="caliper-")

    # Now parse the package names and do the extraction!
    for package in args.packages:
        uri, package = package.split(":")  # pypi:sif
        try:
            manager = get_named_manager(uri, package)
        except NotImplementedError:
            logger.exit("%s is not a valid package manager uri." % package)

        # Create a client to interact with
        client = MetricsExtractor(manager, quiet=True)

        # Do the extraction
        for metric in metrics:
            if metric == "all":
                client.extract_all()
            else:
                client.extract_metric(metric)

        package_dir = os.path.join(outdir, uri.lower(), package)

        # Save results to files
        for _, extractor in client._extractors.items():
            extractor_dir = os.path.join(package_dir, extractor.name)
            mkdir_p(extractor_dir)

            # Write results to file
            write_json(
                extractor.get_file_results(),
                os.path.join(extractor_dir, "%s-file-results.json" % extractor.name),
            )
            write_json(
                extractor.get_summed_results(),
                os.path.join(extractor_dir, "%s-summed-results.json" % extractor.name),
            )

        if not args.no_cleanup:
            client.cleanup(force=True)

    print("Results written to %s" % outdir)
