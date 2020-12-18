__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2020-2021, Vanessa Sochat"
__license__ = "MPL 2.0"

from caliper.utils.file import move_files
import json
import os
import tarfile
import requests
import shutil
import subprocess
import sys


def wget(url, download_to, chunk_size=1024):
    """mimicking wget using requests"""
    response = requests.get(url, stream=True)
    with open(download_to, "wb") as fd:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
                fd.flush()

    return download_to


def wget_and_extract(url, download_to, chunk_size=1024, flatten=True):
    """Given a .tar.gz download url, download to a folder and extract it.
    If flatten is true, we expect a top level folder that should be flattened
    into the current directory.
    """
    download_to = wget(url, download_to)
    download_dir = os.path.dirname(download_to)
    download_root = download_to.rstrip(".tar.gz")
    if download_to.endswith(".tar.gz"):
        tar = tarfile.open(download_to, "r:gz")
        download_root = os.path.join(download_dir, os.path.commonprefix(tar.getnames()))
        tar.extractall(download_dir)
        tar.close()

    # Remove the archive
    if os.path.exists(download_to):
        os.remove(download_to)

    # Move contents into top level folder
    if flatten and os.path.exists(download_root):
        move_files(download_root, download_dir)

    # Remove the originally extracted folder
    if os.path.exists(download_root):
        shutil.rmtree(download_root)
    return download_dir


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


def run_command(
    cmd,
    capture=True,
    environ=None,
    quiet=False,
):

    """run_command uses subprocess to send a command to the terminal. If
    capture is True, we use the parent stdout, so output is piped to the user.
    This means we don't return the output to parse.

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
