"""Functions for finding Cookiecutter templates and other components."""
import logging
import os
from pathlib import Path
from jinja2 import Environment
from cookiecutter.exceptions import NonTemplatedInputDirException
logger = logging.getLogger(__name__)

def find_template(repo_dir: 'os.PathLike[str]', env: Environment) -> Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    :param repo_dir: Local directory of newly cloned repo.
    :return: Relative path to project template.
    """
    repo_dir_path = Path(repo_dir)
    logger.debug('Searching %s for the project template.', repo_dir)

    project_template = None
    for child in repo_dir_path.iterdir():
        if child.is_dir():
            try:
                if child.joinpath('cookiecutter.json').exists():
                    project_template = child
                    break
            except UnicodeDecodeError:
                # Happens when a directory is not readable
                continue

    if project_template:
        project_template_rel = project_template.relative_to(repo_dir_path)
        logger.debug('Project template found at %s', project_template_rel)
        return project_template_rel
    else:
        raise NonTemplatedInputDirException(
            'The repository directory should contain a project template in a subdirectory '
            'or has a cookiecutter.json file in it.'
        )
