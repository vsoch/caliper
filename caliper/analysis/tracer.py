__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2023, Vanessa Sochat"
__license__ = "MPL 2.0"

import os
import re
import sys

_metric = None


class CommandTracer:
    """
    A command tracer takes some function and args/kwargs checks conditions against
    a metric, and then yields some final list of results.
    """

    def trace(self, metric, commands):
        """
        Provide a list of commands and args, e.g.,

        commands = [[pytest.main, ['-xs', testpath1]], [pytest.main, ['-xs', testpath2]]]
        """
        global _metric
        _metric = metric

        for command in commands:
            func, params = command
            if isinstance(params, list):
                sys.settrace(code_tracer)
                func(params)
                sys.settrace(None)
            else:
                sys.settrace(code_tracer)
                func(**params)
                sys.settrace(None)


# local trace function which returns itself
def code_tracer(frame, event, arg=None):
    global _metric

    # extracts frame code
    code = frame.f_code

    # code.co_names is what byte code uses
    # code.co_varnames are all local variable names, starting with args
    # code.co_argcount is the number args
    # split up decorators and args

    args = [x for x in code.co_varnames[: code.co_argcount] if not x.startswith("@")]
    decorators = list(set(code.co_varnames[: code.co_argcount]).difference(set(args)))
    locals = list(code.co_varnames)[code.co_argcount :]

    # Skip these, not sure what to do with them yet
    skips = ["<listcomp>", "<lambda>"]

    # note that frame.f_locals has some local context
    # note that code.co_argcount has argcount
    # Not sure how to derive type here (I don't think we can) but we can get size of stack
    res = {
        "event": event,
        "function": code.co_name,
        "lineno": code.co_firstlineno,
        "stacksize": code.co_stacksize,
        "filename": code.co_filename,
        "args": args,
    }

    # Do we have a class (and name)?
    try:
        cls = frame.f_locals["self"].__class__.__name__
    except (KeyError, AttributeError):
        cls = None
        pass

    if code.co_freevars:
        res["freevars"] = code.co_freevars
    if decorators:
        res["decorators"] = decorators
    if locals:
        res["locals"] = locals

    # We can assume everything found is on the pythonpath
    regex = "(%s|__init__[.]py)" % "|".join(sys.path)
    modulepath = re.sub(regex, "", res["filename"]).strip(os.sep).replace(os.sep, ".")
    modulepath = modulepath.replace(".py", "")

    # Give the result context to compare to a database
    res["module"] = modulepath
    if cls:
        res["path"] = f"{modulepath}.{cls}.{code.co_name}"
    else:
        res["path"] = f"{modulepath}.{code.co_name}"

    # Do not include private modules, and only handle concrete modules for now
    if (
        not modulepath.startswith("_")
        and not re.search("^[<].*[>]$", modulepath)
        and res["function"] not in skips
    ):
        if _metric and hasattr(_metric, "inspect_trace"):
            _metric.inspect_trace(res)

    # TODO we could print pretty here so this is useful outside of a metric
    return code_tracer


def format_results(results):
    """
    Format into prettier json

    This was for the original trace function (not used)
    """
    save = {"calls": {}}

    # This is a tuple (key) and count (value) - we don't care about the value
    for order, (called, count) in enumerate(results.calledfuncs.items()):
        filename, module, function = called
        if filename not in save["calls"]:
            save["calls"][filename] = {
                "module": module,
                "functions": {},
                "order": order,
            }

        # The count should be the only one for the function, but not assuming anything.
        if function not in save["calls"][filename]["functions"]:
            save["calls"][filename]["functions"][function] = 0
        save["calls"][filename]["functions"][function] += count
    return save
