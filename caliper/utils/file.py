__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

import errno
import fnmatch
import json
import io
import os
import shutil
import tempfile
import yaml
import zipfile


def write_zip(members, saveto):
    """Given a dictionary with filenames (keys) and data (values),
    write the data to a zipfile.

    Parameters
    ==========
    members (dict) : a lookup (keys are filenames, values data) of files to add
    saveto   (str) : a filename to save the zip to.
    """
    with zipfile.ZipFile(saveto, "w") as zf:
        for filename, content in members.items():
            if isinstance(content, dict):
                content = json.dumps(content)
            zf.writestr(filename, content)
    return saveto


def read_zip(zipname, filename):
    """read a zipfile into a zipflie object. Optionally extract a specific
    file from it. Currently the only support/need is to extract a specific
    file from it.
    """
    with zipfile.ZipFile(zipname, "r") as zf:
        if not filename:
            return {name: zf.read(name) for name in zf.namelist()}
        elif filename in zf.namelist():
            return zf.read(filename)


def zip_from_string(zipdata, filename=None):
    """Given zipdata (for example, provided from a request) load it into
    a zip object so we can then extract it (or otherwise parse it)
    """
    # Read into in-memory zip, return specific file or lookup of files
    memzip = zipfile.ZipFile(io.BytesIO(zipdata))
    if not filename:
        return {name: memzip.read(name) for name in memzip.namelist()}
    elif filename in memzip.namelist():
        return memzip.read(filename)


def move_files(source, dest):
    """move one or more files from a source to a destination"""
    moved_files = []

    for path in os.listdir(source):
        frompath = os.path.join(source, path)
        topath = os.path.join(dest, path)

        # If a file already exists, remove it
        if os.path.exists(topath) and os.path.isfile(topath):
            os.remove(topath)
        elif os.path.exists(topath) and os.path.isdir(topath):
            shutil.rmtree(topath)

        shutil.move(frompath, dest)
        moved_files.append(topath)
    return moved_files


def get_latest_modified(base, pattern="*.json"):
    """Given a folder, get the latest modified file"""
    files = list(recursive_find(base, pattern))
    if not files:
        return None
    return max(files, key=os.path.getctime)


def recursive_find(base, pattern="*.py"):
    """recursive find will yield python files in all directory levels
    below a base path.

    Arguments:
      - base (str) : the base directory to search
      - pattern: a pattern to match, defaults to *.py
    """
    for root, _, filenames in os.walk(base):
        for filename in fnmatch.filter(filenames, pattern):
            yield os.path.join(root, filename)


def read_file(filename, readlines=True):
    """write_file will open a file, "filename" and write content
    and properly close the file.

    Arguments:
      - filename (str) : the filename to read
      - readlines (bool) : read lines of the file (vs all raw)
    """
    with open(filename, "r") as filey:
        if readlines is True:
            content = filey.readlines()
        else:
            content = filey.read()
    return content


def write_file(filename, content):
    """Write some text content to a file"""
    with open(filename, "w") as fd:
        fd.write(content)


def read_yaml(filename):
    """Given a yaml file, read with pyaml"""
    stream = read_file(filename, readlines=False)
    return yaml.load(stream, Loader=yaml.FullLoader)


def write_json(json_obj, filename, pretty=True):
    """write_json will write a json object to file, pretty printed

    Arguents:
     - json_obj (dict) : the dict to print to json
     - filename (str) : the output file to write to
    """
    with open(filename, "w") as filey:
        if pretty:
            filey.writelines(json.dumps(json_obj, indent=4, separators=(",", ": ")))
        else:
            filey.writelines(json.dumps(json_obj))
    return filename


def read_json(input_file):
    """Read json from an input file.

    Arguments:
      - input_file (str) : the filename to read
    """
    with open(input_file, "r") as filey:
        data = json.loads(filey.read())
    return data


def mkdir_p(path):
    """mkdir_p attempts to get the same functionality as mkdir -p

    Arguments:
     - path (str) : the path to create
    """
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise e


def get_tmpfile(prefix=""):
    """get a temporary file with an optional prefix. By default, the file
    is closed (and just a name returned).

    Arguments:
     - prefix (str) : prefix with this string
    """
    tmpdir = tempfile.gettempdir()
    prefix = os.path.join(tmpdir, os.path.basename(prefix))
    fd, tmp_file = tempfile.mkstemp(prefix=prefix)
    os.close(fd)
    return tmp_file


def get_tmpdir(prefix="", create=True):
    """get a temporary directory for an operation.

    Arguments:
     - prefix (str) : prefix with this string
     - create (bool) : create the folder (defaults to true)
    """
    tmpdir = tempfile.gettempdir()
    prefix = prefix or "rseng-temp"
    prefix = "%s.%s" % (prefix, next(tempfile._get_candidate_names()))
    tmpdir = os.path.join(tmpdir, prefix)
    if not os.path.exists(tmpdir) and create:
        os.mkdir(tmpdir)
    return tmpdir
