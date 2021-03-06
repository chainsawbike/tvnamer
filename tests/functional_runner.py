#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvnamer
#repository:http://github.com/dbr/tvnamer
#license:Creative Commons GNU GPL v2
# http://creativecommons.org/licenses/GPL/2.0/

"""Functional-test runner for use in other tests

Useful functions are run_tvnamer and verify_out_data.

Simple example test:

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = None,
        with_input = "1\ny\n")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)

This runs tvnamer with no custom config (can be a string). It then
sends "1[return]y[return]" to the console UI, and verifies the file was
created correctly, in a way that nosetest displays useful info when an
expected file is not found.
"""

import os
import sys
import shutil
import tempfile
from subprocess import Popen, PIPE

from tvnamer.unicode_helper import p, unicodify


try:
    # os.path.relpath was added in 2.6, use custom implimentation if not found
    relpath = os.path.relpath
except AttributeError:

    def relpath(path, start=None):
        """Return a relative version of a path"""

        if start is None:
            start = os.getcwd()

        start_list = os.path.abspath(start).split(os.path.sep)
        path_list = os.path.abspath(path).split(os.path.sep)

        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
        if not rel_list:
            return os.getcwd()
        return os.path.join(*rel_list)


def make_temp_config(config):
    """Creates a temporary file containing the supplied config (string)
    """
    (fhandle, fname) = tempfile.mkstemp()
    f = open(fname, 'w+')
    f.write(config)
    f.close()

    return fname


def get_tvnamer_path():
    """Gets the path to tvnamer/main.py
    """
    cur_location, _ = os.path.split(os.path.abspath(sys.path[0]))
    for cdir in [".", ".."]:
        tvnamer_location = os.path.abspath(
            os.path.join(cur_location, cdir, "tvnamer", "main.py"))

        if os.path.isfile(tvnamer_location):
            return tvnamer_location
        else:
            p(tvnamer_location)
    else:
        raise IOError("tvnamer/main.py could not be found in . or ..")


def make_temp_dir():
    """Creates a temp folder and returns the path
    """
    return tempfile.mkdtemp()


def make_dummy_files(files, location):
    """Creates dummy files at location.
    """
    dummies = []
    for f in files:
        # Removing leading slash to prevent files being created outside
        # location. This is necessary because..
        # os.path.join('tempdir', '/otherpath/example.avi)
        # ..will return '/otherpath/example.avi'
        if f.startswith("/"):
            f = f.replace("/", "", 1)

        floc = os.path.join(location, f)

        dirnames, _ = os.path.split(floc)
        try:
            os.makedirs(dirnames)
        except OSError, e:
            if e.errno != 17:
                raise

        open(floc, "w").close()
        dummies.append(floc)

    return dummies


def clear_temp_dir(location):
    """Removes file or directory at specified location
    """
    p("Clearing %s" % unicode(location))
    shutil.rmtree(location)


def run_tvnamer(with_files, with_flags = None, with_input = "", with_config = None, run_on_directory = False):
    """Runs tvnamer on list of file-names in with_files.
    with_files is a list of strings.
    with_flags is a list of command line arguments to pass to tvnamer.
    with_input is the sent to tvnamer's stdin
    with_config is a string containing the tvnamer to run tvnamer with.

    Returns a dict with stdout, stderr and a list of files created
    """
    # Create dummy files (config and episodes)
    tvnpath = get_tvnamer_path()
    episodes_location = make_temp_dir()
    dummy_files = make_dummy_files(with_files, episodes_location)

    if with_config is not None:
        configfname = make_temp_config(with_config)
        conf_args = ['-c', configfname]
    else:
        conf_args = []

    if with_flags is None:
        with_flags = []

    if run_on_directory:
        files = [episodes_location]
    else:
        files = dummy_files

    # Construct command
    cmd = [sys.executable, tvnpath] + conf_args + with_flags + files
    p("Running command:")
    p(" ".join(cmd))

    proc = Popen(
        cmd,
        stdout = PIPE,
        stderr = PIPE,
        stdin = PIPE)

    proc.stdin.write(with_input)
    stdout, stderr = proc.communicate()
    stdout, stderr = [unicodify(x) for x in (stdout, stderr)]

    created_files = []
    for walkroot, walkdirs, walkfiles in os.walk(unicode(episodes_location)):
        curlist = [os.path.join(walkroot, name) for name in walkfiles]

        # Remove episodes_location from start of path
        curlist = [relpath(x, episodes_location) for x in curlist]

        created_files.extend(curlist)

    # Clean up dummy files and config
    clear_temp_dir(episodes_location)
    if with_config is not None:
        os.unlink(configfname)

    return {
        'stdout': stdout,
        'stderr': stderr,
        'files': created_files}


def verify_out_data(out_data, expected_files):
    """Verifies the out_data from run_tvnamer contains the expected files.

    Prints the stdout/stderr/files, then asserts all files exist.
    If an assertion fails, nosetest will handily print the stdout/etc.
    """

    p("Expected files:", expected_files)
    p("Got files:", out_data['files'])

    p("\n" + "*" * 20 + "\n")
    p("stdout:\n")
    p(out_data['stdout'])

    p("\n" + "*" * 20 + "\n")
    p("stderr:\n")
    p(out_data['stderr'])

    for cur in expected_files:
        if cur not in out_data['files']:
            raise AssertionError("File named %r not created" % (cur))
