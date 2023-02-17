# Testing Oras Compatibility

In this experiment, we will test the compatibility of latest oras (as defined by its tests trace)
will all previous versions. This requires cloning the latest here:

```bash
$ git clone --depth 1 https://github.com/oras-project/oras-py
```
Installing deps:

```bash
$ cd oras-py
$ pip install -e .
$ cd ../
```

And then exporting the envars needed for the tests:

```bash
export ORAS_HOST=http://127.0.0.1
export ORAS_PORT=5000
```

And then in a separate terminal running a test registry:
```bash
$ docker run -it -e REGISTRY_STORAGE_DELETE_ENABLED=true --rm -p 5000:5000 ghcr.io/oras-project/registry:latest
```
And then the script!

```bash
$ python example.py
```

The script is going to:

1. Generate a database (sqlite) of signatures for oras
2. Create a caliper `CommandTracer` to run against a set of pytest commands (we assume tests pass for the latest release)
3. Assess compatibility or do a diff using the tracer.

### Issues

Issues I see that need to be worked on:

- a decorator means a function can technically allow different args / signature
- lambda / other kinds of calls aren't parsed
- a parent class function will not be known (so we'd need to parse and add on parent signatures?)
- functions defined within functions (e.g., see provider.extract_tags)

## Background

Note that I tried the trace module in python, and it traces but doesn't provide details about function arguments.
I then tried [pytrace](https://github.com/alonho/pytrace), and gawked a little that it was last updated in 2016, and also
has a LGPL license. But I realized the underlying logic is just using [sys.settrace](https://docs.python.org/3/library/sys.html#sys.settrace)
and then making it efficient to save/show results - so we can do that right?

I wound up choosing `call` as the event of interest, because for now the result file is way too big to store
on my computer. I think we might also want to filter down to some set of functions of interest, but we could
also get around this problem by ignoring anything that is part of built-in python. Will there be ABI/compatibility
issues here? Yes, but I think it's a simpler problem to start with the libraries that people install (e.g.,
from conda-forge) and not try to take on system Python yet.

For now these functions are here, but we can invoke from compspec as an analyzer
Note that we will just be assessing compatibility of the latest tests with previous oras versions.
A real world use case would compare some set of tests against deps.
So maybe the entire process should be to generate the database of facts (for all deps)
then run the extraction for a specific version (trace of tests)
and compare up with a matrix of predictions work / not work.

- TODO we will want to create a developer (containerized?) environment for this

The cons of this approach are needing to execute code. But I think with a trace we can get a stronger
signal than just static approaches. And arguably if we are already testing libraries for users on conda
forge, we can just wrap that with this here.
