.. _getting_started-use-cases:

=========
Use Cases
=========

Assess Version Changes
======================

Using the MetricsExtractor, we can start with a package and then calculate metrics
for each version change, and ask questions like:

 - What is the degree of change between minor/major versions?
 - How much do dependencies change over time?
 - How quickly does the package grow?

We might then be able to say that one package is more volatile than another,
and use the metrics in other kinds of analyses.

Break a Workflow
================

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
