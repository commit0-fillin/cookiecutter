"""Helper functions used throughout Cookiecutter."""
import contextlib
import logging
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Dict
from jinja2.ext import Extension
from cookiecutter.environment import StrictEnvironment
logger = logging.getLogger(__name__)

def force_delete(func, path, exc_info):
    """Error handler for `shutil.rmtree()` equivalent to `rm -rf`.

    Usage: `shutil.rmtree(path, onerror=force_delete)`
    From https://docs.python.org/3/library/shutil.html#rmtree-example
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)

def rmtree(path):
    """Remove a directory and all its contents. Like rm -rf on Unix.

    :param path: A directory path.
    """
    shutil.rmtree(path, onerror=force_delete)

def make_sure_path_exists(path: 'os.PathLike[str]') -> None:
    """Ensure that a directory exists.

    :param path: A directory tree path for creation.
    """
    os.makedirs(path, exist_ok=True)

@contextlib.contextmanager
def work_in(dirname=None):
    """Context manager version of os.chdir.

    When exited, returns to the working directory prior to entering.
    """
    curdir = os.getcwd()
    try:
        if dirname is not None:
            os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)

def make_executable(script_path):
    """Make `script_path` executable.

    :param script_path: The file to change
    """
    mode = os.stat(script_path).st_mode
    os.chmod(script_path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

def simple_filter(filter_function):
    """Decorate a function to wrap it in a simplified jinja2 extension."""
    class SimplifiedExtension(Extension):
        def __init__(self, environment):
            super().__init__(environment)
            environment.filters[filter_function.__name__] = filter_function

    return SimplifiedExtension

def create_tmp_repo_dir(repo_dir: 'os.PathLike[str]') -> Path:
    """Create a temporary dir with a copy of the contents of repo_dir."""
    temp_dir = Path(tempfile.mkdtemp())
    shutil.copytree(repo_dir, temp_dir, dirs_exist_ok=True)
    return temp_dir

def create_env_with_context(context: Dict):
    """Create a jinja environment using the provided context."""
    return StrictEnvironment(context=context)
