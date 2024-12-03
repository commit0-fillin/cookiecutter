"""Helper functions for working with version control systems."""
import logging
import os
import subprocess
from pathlib import Path
from shutil import which
from typing import Optional, Tuple
from cookiecutter.exceptions import RepositoryCloneFailed, RepositoryNotFound, UnknownRepoType, VCSNotInstalled
from cookiecutter.prompt import prompt_and_delete
from cookiecutter.utils import make_sure_path_exists
logger = logging.getLogger(__name__)
BRANCH_ERRORS = ['error: pathspec', 'unknown revision']

def identify_repo(repo_url):
    """Determine if `repo_url` should be treated as a URL to a git or hg repo.

    Repos can be identified by prepending "hg+" or "git+" to the repo URL.

    :param repo_url: Repo URL of unknown type.
    :returns: ('git', repo_url), ('hg', repo_url), or None.
    """
    if repo_url.startswith('git+'):
        return 'git', repo_url[4:]
    elif repo_url.startswith('hg+'):
        return 'hg', repo_url[3:]
    elif repo_url.endswith('.git') or 'git' in repo_url:
        return 'git', repo_url
    elif 'bitbucket' in repo_url:
        return 'hg', repo_url
    return None

def is_vcs_installed(repo_type):
    """
    Check if the version control system for a repo type is installed.

    :param repo_type: The type of version control system ('git' or 'hg').
    :return: True if the VCS is installed, False otherwise.
    """
    if repo_type not in ['git', 'hg']:
        return False
    
    try:
        subprocess.run([repo_type, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def clone(repo_url: str, checkout: Optional[str]=None, clone_to_dir: 'os.PathLike[str]'='.', no_input: bool=False):
    """Clone a repo to the current directory.

    :param repo_url: Repo URL of unknown type.
    :param checkout: The branch, tag or commit ID to checkout after clone.
    :param clone_to_dir: The directory to clone to.
                         Defaults to the current directory.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :returns: str with path to the new directory of the repository.
    """
    repo_type, repo_url = identify_repo(repo_url)
    if repo_type is None:
        raise UnknownRepoType(f"Couldn't determine repository type for {repo_url}")

    if not is_vcs_installed(repo_type):
        raise VCSNotInstalled(f"{repo_type} is not installed.")

    clone_to_dir = Path(clone_to_dir).resolve()
    make_sure_path_exists(clone_to_dir)

    repo_dir = clone_to_dir / Path(repo_url).name.rsplit('.', 1)[0]

    if repo_dir.exists() and not no_input:
        if not prompt_and_delete(repo_dir):
            return str(repo_dir)

    if repo_type == 'git':
        clone_cmd = ['git', 'clone']
        if checkout:
            clone_cmd.extend(['-b', checkout])
        clone_cmd.extend([repo_url, str(repo_dir)])
    elif repo_type == 'hg':
        clone_cmd = ['hg', 'clone']
        if checkout:
            clone_cmd.extend(['-u', checkout])
        clone_cmd.extend([repo_url, str(repo_dir)])

    try:
        subprocess.run(clone_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise RepositoryCloneFailed(f"Failed to clone {repo_url}. Error: {e.stderr.decode('utf-8')}")

    if checkout and repo_type == 'git':
        try:
            subprocess.run(['git', 'checkout', checkout], cwd=repo_dir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8')
            if any(err in error_msg for err in BRANCH_ERRORS):
                subprocess.run(['git', 'checkout', '-b', checkout], cwd=repo_dir, check=True)
            else:
                raise RepositoryCloneFailed(f"Failed to checkout {checkout}. Error: {error_msg}")

    return str(repo_dir)
