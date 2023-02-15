#!/usr/bin/env/python3

# This is one way to get releases!
# import json
import os
import sys

import pytest

from caliper.managers import PypiManager
from caliper.metrics import MetricsExtractor

here = os.path.abspath(os.path.dirname(__file__))

results = {}
sig = None


def main():
    # For this first part, we will create a manager and extract complete data for it
    manager = PypiManager("oras")

    # Just do two specs for a diff
    extractor = MetricsExtractor(manager)

    # This repository will have each release version represented as a tagged commit
    extractor.prepare_repository()

    # Extract metric for compspec
    metric = extractor.extract_metric("compspec")

    # How to get results
    data = metric.get_results()
    assert data

    # Just save to file and cleanup
    metric.save_json("./data", force=True)
    extractor.cleanup(force=True)

    # For this second part, we will target an oras clone and try to trace the tests.
    # This also means we need the environment set up, but this is just for testing
    # docker run -it -e REGISTRY_STORAGE_DELETE_ENABLED=true --rm -p 5000:5000 ghcr.io/oras-project/registry:latest
    # export ORAS_HOST=http://127.0.0.1
    # export ORAS_PORT=5000
    oras_clone = os.path.join(here, "oras-py")
    if not os.path.exists(oras_clone):
        sys.exit(
            "Please clone oras to oras-py here, e.g., git clone --depth 1 https://github.com/oras-project/oras-py"
        )

    # The result files are so big, just try saving one
    testpaths = ["oras-py/oras/tests/test_utils.py"]
    for testpath in testpaths:
        # hacky way to pass forward script name and current result set
        global script
        global sig
        script = testpath
        for signature in data:
            sig = data[signature]

        # Wrap the trace around calling the pytest function
        # okay wow - for small tests this produces over a million lines!!
        # instead, let's create (for each version) a lookup we care about,
        # and ONLY stop if we find a mismatch
        sys.settrace(code_tracer)
        pytest.main(["-xs", testpath])
        sys.settrace(None)

    # Write the trace output to file
    # with open("./oras_trace_results.json", "w") as fd:
    #    fd.write(json.dumps(results, indent=4))


# local trace function which returns itself
def code_tracer(frame, event, arg=None):
    global script
    global results
    global sig
    if script not in results:
        results[script] = []

    # extracts frame code
    code = frame.f_code

    # note that frame.f_locals has some local context
    # note that code.co_argcount has argcount
    # Not sure how to derive type here (I don't think we can) but we can get size of stack
    res = {
        "event": event,
        "function": code.co_name,
        "lineno": code.co_firstlineno,
        "stacksize": code.co_stacksize,
        "filename": code.co_filename,
        "args": code.co_varnames,
    }
    if code.co_freevars:
        res["freevars"] = code.co_freevars

    # TODO how to filter to imports of interest?
    # Just look at function calls for now
    if event == "call" and "oras" in res["filename"]:
        results[script].append(res)
        # NEXT STEPS: we need to efficiently query some database for each function
        # of interest, and if we find the module is defined, determine if something
        # is missing/ different.

        # This is a bad/hard coded way to get path, just for this experiment
        # module = res['filename'].split('oras-py')[-1].replace(os.sep, '.').strip('.')
        # if module.endswith('__init__.py'):
        #    module = module.replace('__init__.py', '').strip('.')
        # module = module.replace('.py', '')

        # We can't be sure what level the definition is at
        # found = False

        # TODO need to split and re-assemble module name
        # for part in module.split('.'):

        # Do we have the signature?
        # Note this is also hard coded manual check / proof of concept eventually
        # if part in sig:

        # We found the module, we're good
        # if res['function'] == '<module>':
        # found = True
        # break

        # Case 1: function missing
        # if res['function'] not in sig[module]:
        #    continue
        # print(res)

        # if not found:
        # print(f'MISSING signature for {module}')

    #        results[script].append(res)
    return code_tracer

    # attempt 1 with trace - this isn't super fast!
    # and it is missing the args/etc
    # tracer = trace.Trace(count=False, trace=True, countfuncs=True)
    # tracer.run(f'pytest.main(["-xs", "{testpath}"])')
    # results[testpath] = format_results(tracer.results())


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


if __name__ == "__main__":
    main()
