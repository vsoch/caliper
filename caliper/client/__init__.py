#!/usr/bin/env python

__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import caliper
import argparse
import sys
import logging


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

    # Generate a key for the interface
    extract = subparsers.add_parser(
        "extract",
        help="extract one or more metrics for a software package.",
    )

    extract.add_argument("--metric", nargs="*", help="one or more metrics to extract")
    extract.add_argument(
        "packages",
        help="Packages to extract, e.g., pypi, GitHub, or (eventually) spack.",
        nargs="?",
        default=None,
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

    # If the user didn't provide any arguments, show the full help
    if len(sys.argv) == 1:
        help()

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()

    # TODO import setup_logger to add the logging level

    # Show the version and exit
    if args.command == "version" or args.version:
        print(caliper.__version__)
        sys.exit(0)

    # Does the user want a shell?
    main = None
    # if args.command == "extract":
    #    from .extract import main

    print("This client has not been developed yet.")
    if main is not None:
        main(args=args, extra=extra)


#    else:
#        help()


if __name__ == "__main__":
    main()
