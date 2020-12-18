# Caliper

[![PyPI version](https://badge.fury.io/py/rseng.svg)](https://badge.fury.io/py/caliper)

Caliper is a tool for measuring and assessing change in packages.

**under development**

## Core

### Concepts

 - **Manager** a handle to interact with a package manager
 - **Extractor** a controller to use a manager to extract metrics of interest
 - **Version repository** a repository created by an extractor that tagged commits for package releases

### Managers

A manager is a handle to interact with a package.

#### Pypi

The first kind of package we are interested in is one from pypi.
For example, we can create a new manager as follows:

```python
from caliper.managers import PypiManager
manager = PypiManager("sregistry")
```

The manager specs include the source archive, version, and hash for each version
of the package. The schema of the spec is a subset of the spack package schema.
Every manager exposes this metadata.

```python
manager.specs[0]
Found 82 versions for sregistry
{'name': 'sregistry',
 'version': '0.0.1',
 'source': {'filename': 'https://files.pythonhosted.org/packages/ef/2f/ccc36e816dc081abbe0932c422586eda868719025ec07ac206ed254d6a3c/sregistry-0.0.1.tar.gz',
  'type': 'source'},
 'hash': 'd4ee6933321b5a3da13e0b1657ca74f90477f670e59096a6a0a4dbb30a0b1f07'}

manager.specs[-1]
{'name': 'sregistry',
 'version': '0.2.36',
 'source': {'filename': 'https://files.pythonhosted.org/packages/75/6c/2b5bcf0191c0ddc9b95dd156d827c8d80fa8fe86f01f7a053fdd97eaea41/sregistry-0.2.36.tar.gz',
  'type': 'source'},
 'hash': '238ebd3ca0e0408e0be6780d45deca79583ce99aed05ac6981da7a2b375ae79e'}
```

#### GitManager

A GitManager is a special kind of manager that exists to interact with a git repository.
It will be possible to use it as a manager proper (not yet developed) but it can also
serve to create and interact with local git repositories. For example, let's create
a temporary directory, add stuff to it, commit and then tag it.

```python
from caliper.managers import GitManager
import tempfile
git = GitManager(tempfile.mkdtemp())
git.init()

# copy content to the repository here

git.commit("Adding new content!")
git.tag("tag")
```

You can imagine how this might be used - we can have a class that can take a manager,
and then iterate over versions/releases and create a tagged commit for each.
We can then easily extract metrics about files changed between versions.
This is the [metrics extractor](#metrics-extractor) discussed next.

### Metrics Extractor

Finally, a metrics extractor provides an easy interface to iterate over versions
of a package, and extract some kind of metric. For example, let's say we have
the Pypi manager above:

```python
from caliper.managers import PypiManager
manager = PypiManager("sregistry")

manager
# [manager:sregistry]
```

We can then hand it off to the extractor:

```python
from caliper.metrics import MetricsExtractor
extractor = MetricsExtractor(manager)

# This repository will have each release version represented as a tagged commit
repo = extractor.prepare_repository()
```
```
...
[master b45263b] 0.2.34
 8 files changed, 60 insertions(+), 65 deletions(-)
[master 555962b] 0.2.35
 4 files changed, 4 insertions(+), 4 deletions(-)
[master ead9302] 0.2.36
 117 files changed, 141 insertions(+), 141 deletions(-)
Repository for [manager:sregistry] is created at /tmp/sregistry-j63wuvei
```

At this point you'll see the extractor iterating through each repository version,
and commiting changes based on the version. It's fun to open the repository folder 
(in /tmp named based on the package) and watch the changes happening in real time.
At this point we would have our **version repository** that we can calculate metrics
over. For example, we can see commits that correspond to versions:

```bash
$ git log
commit ead9302cec47e62f8eabc5aefc0e55eeb3b8d717 (HEAD -> master, tag: 0.2.36)
Author: vsoch <vsochat@stanford.edu>
Date:   Fri Dec 18 14:51:34 2020 -0700

    0.2.36

commit 555962bad5f9e6d0d8ea4c4ea6bb0bdcb92d12f3 (tag: 0.2.35)
Author: vsoch <vsochat@stanford.edu>
Date:   Fri Dec 18 14:51:34 2020 -0700

    0.2.35

commit b45263b9c4da6aef096d49cc222bb9c64d2f6997 (tag: 0.2.34)
Author: vsoch <vsochat@stanford.edu>
Date:   Fri Dec 18 14:51:34 2020 -0700

    0.2.34

commit 113bc796acbffc593d400a19471c56c36289d764 (tag: 0.2.33)
Author: vsoch <vsochat@stanford.edu>
Date:   Fri Dec 18 14:51:33 2020 -0700
...
```

We can see the tags:

```bash
$ git tag
0.0.1
0.0.2
0.0.3
...
0.2.34
0.2.35
0.2.36
```

This is really neat! Next we can use the extractor to calculate metrics.

**under development**


## Use Cases

## Assess Version Changes

Using the MetricsExtractor, we can start with a package and then calculate metrics
for each version change, and ask questions like:

 - What is the degree of change between minor/major versions?
 - How much do dependencies change over time?
 - How quickly does the package grow?

We might then be able to say that one package is more volatile than another,
and use the metrics in other kinds of analyses.

## Break a Workflow

An interesting use case for caliper is to use metrics to figure out if we can 
predict breaking. For example, we might have:

1. A Dockerfile with an entrypoint and command that generates some output
2. A list of requirements defined in a requirements.txt file (or similar)

And then we might derive a baseline container to run the workflow in question, and then vary
package versions to determine if the container is still able to run and
produce the same result, or if the dependency cannot be resolved all together.
We can then assess, based on ranges of package versions that work vs. not and the
degree of changes for each:

1. The degree to which some version increment is likely to break a build or run and
2. How close the developer was to representing a "correct" set of versions.

"Correct" is in quotes because we cannot easily assess dependency interaction
(but perhaps can make some kind of proxy for it eventually). 

**Note** this is all still being developed, and likely to change!

## License

 * Free software: MPL 2.0 License
