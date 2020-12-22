__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.utils.file import mkdir_p, read_file, write_file
from caliper.logger import logger
import os

here = os.path.abspath(os.path.dirname(__file__))

try:
    from jinja2 import Template
except ImportError:
    logger.exit("You must install jinja2 to use graphs.")


def generate_graph(template, data, outdir, force):
    """given an html template, data to populate it, and an output directory,
    generate a plot. Known data attributes are:

      - datasets: a list of dataset, each having color, name, and values
      - title: the title for the html page

     Of course the template and data can be matched for each metric.
    """
    filename = os.path.join(outdir, "index.html")
    if os.path.exists(filename) and not force:
        logger.exit("%s exists, use --force to overwrite." % filename)
    template = Template("".join(read_file(template)))
    result = template.render(**data)
    if not os.path.exists(outdir):
        mkdir_p(outdir)
    write_file(filename, result)
    logger.info("Output written to %s" % filename)
