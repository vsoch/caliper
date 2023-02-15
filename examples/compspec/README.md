# Composition Spec Types

This is an experiment to extract ABI corpora (facts about a libraries surface, or imports and exports).
We are using caliper and creating a "compspec" extraction type, and on this backend we can
technically use any tool that makes sense.

<p align="center">
  <img height="300" src="https://raw.githubusercontent.com/compspec/spec/main/img/compspec-circle.png">
</p>

## Definitions

The following definitions are important when working with a composition specification:

 - A **corpus** is a set of facts that describe an entire library (in isolation) - this would be a full extraction to save somewhere. It includes:
   - **imports**: what the library needs
   - **exports**: what the library provides
 - A **surface** is the set of facts that are available for other libraries to use ("exports")
 - A **diff** is taking the difference between two corpora, e.g., Library A version 1 and Library A version 2, we would see changes.
 - A **trace** is exactly that, and providing a complete list of calls that a function / module makes to assess what corpora would work.

I really like the idea of being able to trace, for example, tests, and for library releases (I think?) we can have some confidence that tests will
work given some testing environment. However, this gets complex in that not all libraries have tests, not all libraries have good, representative tests, and the tests (with the trace) would only reflect one specific version of a library. E.g., we would have to assume the calls / structure stays consistent to "swap in" other versions of deps and assess if they work (and maybe that is OK to do). What I don't like about the idea is that it wouldn't be reliable to test any library, no matter what (no tests, no go!) We arguably want a method that works when there are not tests.

## Composition Specification

### Python

This is the generic data structure we can use to describe the corpus of a library.
Importantly, we want to flatten things out to make it easier to parse than having
to deal with a graph. First, install development caliper with compspec:

```bash
$ pip install -e .[compspec]
```

And then run the example:

```bash
$ python example.py
```

## Comparison Types

The first part of this work defines data structures that might define different types of language-specific
comparisons (that can be used to generate or detect compatibility issues).
Since we are primarily interested in python to start, Python is provided here.
For now, each is represented in a yaml file named in the format `<language>-types.yaml`.

 - [python](python-types.yaml): Types of changes (that can lead to incompatibility) for Python

To start, we would want to be able to use any particular tool to detect a specific kind of change.
As an example:

```yaml
  - uid: function-removal
    level: module
    description: Remove a function from a module
```

Removing a function from a class would obviously have bad consequences if a library depends on it.
If we imagine a simple case, we can derive a lot of information about the interactions
between module_a and b from imports alone:

```python
from module_a import function_a

def foo()
    function_a()
```

We don't necessarily need to know that function_a is called in foo because we see the import.
In a different case, someone might do:

```python
import module_a

def foo()
    module_a.function_a()
```

And we don't have information from the import alone about what functions are needed.
In this case we either would need to statically parse where module_a is used, or we would
need to assume that everything is needed (and should be assessed for change). The same issue
might happen for a class. Here is our data attribute for a class function removal:

```yaml
  - uid: class-function-removal
    level: class
    description: Remove a function from a class
```

And then a simple removal case shows that we would again need to parse within
a function to see that "do" is called.

```
# Library A

from library_b import ClassName

def foo():
    myclass = ClassName()
    myclass.do()
```

## TODO

- [x] update caliper to have a "compspec" type that uses jedi and outputs a more organized (typed) format
- [x] generate facts across versions of a library (oras)
- [x] think about concepts of a diff vs. trace (a diff compares across versions, and a trace gets signatures used for a call or set of tests)
- [x] likely we want a conda manager!
- try tracing with https://github.com/alonho/pytrace/tree/master
