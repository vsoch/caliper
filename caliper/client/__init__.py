#!/usr/bin/env python

__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import caliper
from caliper.logger import setup_logger
from caliper.managers.base import ManagerBase
import argparse
import sys


def get_parser():

    parser = argparse.ArgumentParser(
        description="Caliper is a tool for measuring and assessing changes in packages."
    )

    parser.add_argument(
        "--version",
        dest="version",
        help="suppress additional output.",
        default=False,
        action="store_true",
    )

    description = "actions"
    subparsers = parser.add_subparsers(
        help="actions",
        title="actions",
        description=description,
        dest="command",
    )

    # print version and exit
    subparsers.add_parser("version", help="show software version")

    # See metrics available
    metrics = subparsers.add_parser(
        "metrics",
        help="see metrics available",
    )

    metrics.add_argument(
        "query",
        help="search metrics by a query string",
        nargs="?",
        default=None,
    )

    analyze = subparsers.add_parser(
        "analyze",
        help="analyze functionality of a package.",
    )

    analyze.add_argument(
        "--config",
        help="A caliper.yaml file to use for the analysis (required)",
        default="caliper.yaml",
    )

    analyze.add_argument(
        "--no-progress",
        dest="no_progress",
        help="Do not show a progress bar (defaults to unset, showing progress)",
        default=False,
        action="store_true",
    )

    # serial argument removed for analyze, doesn't run well building containers

    analyze.add_argument(
        "--force",
        dest="force",
        help="If an output file exists, force re-write (default will not overwrite)",
        default=False,
        action="store_true",
    )

    analyze.add_argument(
        "--cleanup",
        dest="cleanup",
        help="Do docker system prune --all after each build, recommended for saving space.",
        default=False,
        action="store_true",
    )

    analyze.add_argument(
        "--nprocs",
        dest="nprocs",
        help="Number of processes. Defaults to cpu count.",
        type=int,
    )

    extract = subparsers.add_parser(
        "extract",
        help="extract one or more metrics for a software package.",
    )

    extract.add_argument(
        "--metric",
        help="one or more metrics to extract (comma separated), defaults to all metrics",
        default="all",
    )

    extract.add_argument(
        "--versions",
        help="one or more versions to extract (comma separated), defaults to all versions",
    )

    extract.add_argument(
        "-f",
        "--fmt",
        "--format",
        dest="fmt",
        help="the format to extract. Defaults to json (multiple files).",
        choices=ManagerBase.export_formats + [None],
        default=None,
    )

    extract.add_argument(
        "packages",
        help="package to extract, e.g., pypi:, github:",
        nargs="*",
        default=None,
    )

    extract.add_argument(
        "--no-cleanup",
        dest="no_cleanup",
        help="do not cleanup temporary extraction repositories.",
        default=False,
        action="store_true",
    )

    update = subparsers.add_parser(
        "update",
        help="update an extraction for one or more software packages.",
    )

    update.add_argument(
        "--metric",
        help="one or more metrics to update (comma separated), defaults to all metrics",
        default="all",
    )

    update.add_argument(
        "-f",
        "--fmt",
        "--format",
        dest="fmt",
        help="the format to update. Defaults to existing format in repository.",
        choices=ManagerBase.export_formats + [None],
        default=None,
    )

    update.add_argument(
        "--config",
        help="A caliper.yaml file to use for the update (required)",
        default="caliper.yaml",
    )

    update.add_argument(
        "packages",
        help="package to extract, e.g., pypi:, github:, if caliper.yaml not provided",
        nargs="*",
        default=None,
    )

    update.add_argument(
        "--check",
        dest="check",
        help="only check for updates and print status to the terminal.",
        default=False,
        action="store_true",
    )

    update.add_argument(
        "--outdir",
        help="output directory to write files (defaults to present working directory)",
        default=None,
    )

    view = subparsers.add_parser(
        "view",
        help="extract a metric and view a plot.",
    )

    view.add_argument(
        "--metric",
        help="a metric to extract",
    )

    view.add_argument(
        "--title",
        help="the title for the graph (defaults to one set by metric)",
    )

    view.add_argument(
        "input",
        help="input data file to visualize.",
    )

    # Logging
    logging_group = parser.add_argument_group("LOGGING")

    logging_group.add_argument(
        "--quiet",
        dest="quiet",
        help="suppress logging.",
        default=False,
        action="store_true",
    )

    logging_group.add_argument(
        "--verbose",
        dest="verbose",
        help="verbose output for logging.",
        default=False,
        action="store_true",
    )

    logging_group.add_argument(
        "--log-disable-color",
        dest="disable_color",
        default=False,
        help="Disable color for caliper logging.",
        action="store_true",
    )

    logging_group.add_argument(
        "--log-use-threads",
        dest="use_threads",
        action="store_true",
        help="Force threads rather than processes.",
    )

    for command in [extract, view]:
        command.add_argument(
            "--outdir",
            help="output directory to write files.",
            default=None,
        )

        command.add_argument(
            "--force",
            dest="force",
            help="if a file exists, do not overwrite.",
            default=False,
            action="store_true",
        )

    return parser


def main():
    """main entrypoint for rse"""

    parser = get_parser()

    def help(return_code=0):
        """print help, including the software version and active client
        and exit with return code.
        """
        version = caliper.__version__

        print("\ncaliper Python v%s" % version)
        parser.print_help()
        sys.exit(return_code)

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()

    # customize logging
    setup_logger(
        quiet=args.quiet,
        nocolor=args.disable_color,
        debug=args.verbose,
        use_threads=args.use_threads,
    )

    # Show the version and exit
    if args.command == "version" or args.version:
        print(caliper.__version__)
        sys.exit(0)

    main = None
    if args.command == "analyze":
        from .analyze import main
    elif args.command == "extract":
        from .extract import main
    elif args.command == "metrics":
        from .metrics import main
    elif args.command == "update":
        from .update import main
    elif args.command == "view":
        from .view import main

    if main is not None:
        main(args=args, extra=extra)
    else:
        help()


if __name__ == "__main__":
    main()
