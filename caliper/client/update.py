__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics import MetricsUpdater
from caliper.logger import logger
from caliper.utils.file import read_yaml
import os


def main(args, extra):

    # The config file must exist if packages are not defined
    if not args.packages and (not args.config or not os.path.exists(args.config)):
        logger.exit(
            "You must provide an existing caliper.yaml config with --config, or --packages."
        )

    # Ensure that all metrics are valid
    client = MetricsUpdater(quiet=True)
    metrics = args.metric.split(",")

    # If asking for all, we will do all regardless of other specifications
    if "all" in metrics:
        metrics = list(client.metrics)

    for metric in metrics:
        if metric not in client.metrics:
            logger.exit("%s is not a known metric." % metric)

    # prepare top level output directory
    outdir = args.outdir or os.getcwd()

    # Read packages from the config, if provided
    packages = args.packages
    if not packages and args.config:
        config = read_yaml(args.config)
        packages = [x["name"] for x in config.get("metrics", []) if x.get("name")]
        metrics = [x.get("metrics", metrics) for x in config.get("metrics", [])]
    else:
        metrics = [metrics for x in range(len(packages))]

    # Check or Update the package metrics
    if args.check:
        missing = client.check_metrics(packages, metrics, outdir, quiet=True)
        for package, metrics in missing.items():
            if not metrics:
                print("[👀️ ] %s is not found." % package)
                continue
            for metric, versions in metrics.items():

                if not versions:
                    print("[✔️  ] %s|%s is up to date." % (package, metric))
                else:
                    print(
                        "[✖️  ] %s|%s has %s new versions."
                        % (package, metric, len(versions))
                    )

    else:
        client.update_metrics(packages, metrics, outdir)
