__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.utils.file import move_files
from caliper.logger import logger
import json
import os
import requests
import shutil
import subprocess
import sys
import tarfile
import threading
import zipfile


def wget(url, download_to, chunk_size=1024):
    """mimicking wget using requests"""
    response = requests.get(url, stream=True)
    with open(download_to, "wb") as fd:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
                fd.flush()

    return download_to


def wget_and_extract(
    url, download_to, download_type="targz", chunk_size=1024, flatten=True
):
    """Given a download url of a particular type (targz or wheel or zip)
    download to a folder and extract it. If flatten is true, we expect a top
    level folder that should be flattened into the current directory.
    """
    if download_type == "targz":
        dest, root, dest_dir = wget_and_extract_targz(url, download_to, chunk_size)
    elif download_type in ["wheel", "gzip", "zip"]:
        dest, root, dest_dir = wget_and_extract_zip(url, download_to, chunk_size)
    else:
        logger.exit("%s is not a known archive type." % download_type)

    # Remove the archive
    if os.path.exists(dest):
        os.remove(dest)

    # Move contents into top level folder
    if flatten and os.path.exists(root):
        move_files(root, dest_dir)

    # Remove the originally extracted folder
    if os.path.exists(root):
        shutil.rmtree(root)
    return dest_dir


def wget_and_extract_targz(url, download_to, chunk_size=1024):
    """Get an extract a targz archive."""
    download_to = wget(url, download_to, chunk_size=chunk_size)
    download_dir = os.path.dirname(download_to)
    download_root = download_to.rstrip(".tar.gz")

    # Extract tar and determine root folder
    with tarfile.open(download_to, "r:gz") as tar:
        download_root = os.path.join(download_dir, os.path.commonprefix(tar.getnames()))
        tar.extractall(download_dir)

    return download_to, download_root, download_dir


def wget_and_extract_zip(url, download_to, chunk_size=1024):
    """Get an extract a zip or wheel archive."""
    download_to = wget(url, download_to, chunk_size=chunk_size)
    download_root = download_to.rsplit(".", 1)[0]
    download_dir = os.path.dirname(download_to)

    with zipfile.ZipFile(download_to, "r") as zip_ref:
        top_level = {item.split("/")[0] for item in zip_ref.namelist()}
        zip_ref.extractall(download_dir)

    # For wheels, remove dist-info, set download_root to unpack
    for folder in top_level:
        folder_dir = os.path.join(download_dir, folder)
        if folder.endswith(".dist-info") and os.path.exists(folder_dir):
            shutil.rmtree(folder_dir)
        elif folder.endswith(".data") and os.path.exists(folder_dir):
            download_root = folder_dir

    return download_to, download_root, download_dir


def do_request(url, headers=None, data=None, method="GET"):
    """A general function to do a request, and handle any possible error
    codes.
    """
    response = requests.request(method, url, headers=headers, data=json.dumps(data))

    if response.status_code not in [200, 201]:

        # Try to serialize the message, if possible
        try:
            message = response.json()
        except:
            message = ""
        sys.exit(
            f"Error with {url}: {response.status_code}, {response.reason}\n{message}"
        )

    return response.json()


def decodeUtf8String(inputStr):
    """Convert an UTF8 sequence into a string
    Required for compatibility with Python 2 where str==bytes
    inputStr -- Either a str or bytes instance with UTF8 encoding
    """
    return (
        inputStr
        if isinstance(inputStr, str) or not isinstance(inputStr, bytes)
        else inputStr.decode("utf8")
    )


class CommandRunner(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.error = []
        self.output = []
        self.retval = None

    def reader(self, stream, context):
        """Get output and error lines and save to command runner."""
        # Make sure we save to the correct field
        lines = self.error
        if context == "stdout":
            lines = self.output

        while True:
            s = stream.readline()
            if not s:
                break
            lines.append(s.decode("utf-8"))
        stream.close()

    def run_command(self, cmd, env=None, **kwargs):
        self.reset()

        # If we need to update the environment
        # **IMPORTANT: this will include envars from host. Absolutely cannot
        # be any secrets (they should be defined in the app settings file)
        envars = os.environ.copy()
        if env:
            envars.update(env)

        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=envars, **kwargs
        )

        # Create threads for error and output
        t1 = threading.Thread(target=self.reader, args=(p.stdout, "stdout"))
        t1.start()
        t2 = threading.Thread(target=self.reader, args=(p.stderr, "stderr"))
        t2.start()

        p.wait()
        t1.join()
        t2.join()
        self.retval = p.returncode
        return self.output


def run_command(
    cmd,
    capture=True,
    environ=None,
    quiet=False,
):

    """run_command uses subprocess to send a command to the terminal. If
    capture is True, we use the parent stdout, so output is piped to the user.
    This means we don't return the output to parse. This is a function (simpler)
    version of the Command Runner that also supports printing out output.

    Arguments
    =========
    cmd: the command to send, should be a list for subprocess
    capture: if True, don't set stdout and have it go to console. This
             option can print a progress bar, but won't return the lines
             as output.

    Returns
    =======
    result (dict) : with return_code and lines (list of output lines)
    """
    stdout = None
    if capture:
        stdout = subprocess.PIPE

    # Use the parent stdout and stderr
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=stdout, env=environ)
    lines = []

    for line in process.communicate():
        if line:
            line = decodeUtf8String(line)
            lines.append(line)
            if not quiet:
                sys.stdout.write(line)

    output = {"lines": lines, "return_code": process.returncode}
    return output
