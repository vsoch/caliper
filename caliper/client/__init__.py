#!/usr/bin/env python

__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import caliper
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

    for command in [extract, view]:
        command.add_argument(
            "--outdir",
            help="output directory to write files (defaults to temporary directory)",
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

    # TODO import setup_logger to add the logging level

    # Show the version and exit
    if args.command == "version" or args.version:
        print(caliper.__version__)
        sys.exit(0)

    main = None
    if args.command == "extract":
        from .extract import main
    elif args.command == "metrics":
        from .metrics import main
    elif args.command == "view":
        from .view import main

    if main is not None:
        main(args=args, extra=extra)
    else:
        help()


if __name__ == "__main__":
    main()
