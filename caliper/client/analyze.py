__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.analysis import CaliperAnalyzer
from caliper.logger import logger
import os


def main(args, extra):

    # The config file must exist
    if not args.config or not os.path.exists(args.config):
        logger.exit("You must provide an existing caliper.yaml config with --config.")

    client = CaliperAnalyzer(args.config)
    analyzer = client.get_analyzer()

    # serial argument removed for analyze, doesn't run well building containers
    analyzer.run_analysis(
        show_progress=not args.no_progress,
        nproc=args.nprocs,
        force=args.force,
        parallel=False,
        cleanup=args.cleanup,
    )
