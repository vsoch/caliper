__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.metrics import MetricsExtractor
from caliper.logger import logger
import os


def main(args, extra):

    # Ensure that all metrics are valid
    client = MetricsExtractor(quiet=True)

    # If the outdir is the present working directory
    outdir = os.getcwd() if args.outdir == "." else args.outdir

    # An input is required!
    if not args.input:
        logger.exit("An input results file is required.")

    # If the metric is not provided on the command line, needs to be in filename
    metric = args.metric or os.path.basename(args.input).split("-")[0]

    if not metric:
        logger.exit("You must provide a --metric, not derivable from filename.")
    if metric not in client.metrics:
        logger.exit("%s is not a known metric." % metric)

    # prepare top level output directory
    outdir = args.outdir or os.getcwd()
    metric = client.get_metric(metric)
    metric.plot_results(args.input, outdir, force=args.force, title=args.title)
