"""Functions for generating a project from a project template."""
import fnmatch
import json
import logging
import os
import shutil
import warnings
from collections import OrderedDict
from pathlib import Path
from binaryornot.check import is_binary
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateSyntaxError, UndefinedError
from cookiecutter.exceptions import ContextDecodingException, OutputDirExistsException, UndefinedVariableInTemplate
from cookiecutter.find import find_template
from cookiecutter.hooks import run_hook_from_repo_dir
from cookiecutter.utils import create_env_with_context, make_sure_path_exists, rmtree, work_in
logger = logging.getLogger(__name__)

def is_copy_only_path(path, context):
    """Check whether the given `path` should only be copied and not rendered.

    Returns True if `path` matches a pattern in the given `context` dict,
    otherwise False.

    :param path: A file-system path referring to a file or dir that
        should be rendered or just copied.
    :param context: cookiecutter context.
    """
    copy_without_render = context.get('_copy_without_render', [])
    for pattern in copy_without_render:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False

def apply_overwrites_to_context(context, overwrite_context, *, in_dictionary_variable=False):
    """Modify the given context in place based on the overwrite_context."""
    for key, value in overwrite_context.items():
        if isinstance(value, dict):
            if key not in context:
                context[key] = {}
            apply_overwrites_to_context(context[key], value, in_dictionary_variable=True)
        elif isinstance(value, list):
            if key not in context:
                context[key] = []
            context[key].extend(value)
        else:
            if in_dictionary_variable:
                context[key] = value
            else:
                context[key] = str(value)

def generate_context(context_file='cookiecutter.json', default_context=None, extra_context=None):
    """Generate the context for a Cookiecutter project template.

    Loads the JSON file as a Python object, with key being the JSON filename.

    :param context_file: JSON file containing key/value pairs for populating
        the cookiecutter's variables.
    :param default_context: Dictionary containing config to take into account.
    :param extra_context: Dictionary containing configuration overrides
    """
    context = {}
    try:
        with open(context_file) as file_handle:
            obj = json.load(file_handle, object_pairs_hook=OrderedDict)
        context = obj if isinstance(obj, dict) else obj[0]
    except ValueError as e:
        raise ContextDecodingException(
            f"JSON decoding error while loading '{context_file}': {e}"
        )

    # Add default context values
    if default_context:
        apply_overwrites_to_context(context, default_context)

    # Add extra_context values
    if extra_context:
        apply_overwrites_to_context(context, extra_context)

    return context

def generate_file(project_dir, infile, context, env, skip_if_file_exists=False):
    """Render filename of infile as name of outfile, handle infile correctly.

    Dealing with infile appropriately:

        a. If infile is a binary file, copy it over without rendering.
        b. If infile is a text file, render its contents and write the
           rendered infile to outfile.

    Precondition:

        When calling `generate_file()`, the root template dir must be the
        current working directory. Using `utils.work_in()` is the recommended
        way to perform this directory change.

    :param project_dir: Absolute path to the resulting generated project.
    :param infile: Input file to generate the file from. Relative to the root
        template dir.
    :param context: Dict for populating the cookiecutter's variables.
    :param env: Jinja2 template execution environment.
    """
    logger.debug('Generating file %s', infile)

    # Render the path to the output file (not the contents of the input file)
    outfile_tmpl = env.from_string(infile)
    outfile = os.path.join(project_dir, outfile_tmpl.render(**context))
    logger.debug('Project dir is %s', project_dir)
    logger.debug('Output file is %s', outfile)

    # Create the containing directory if it doesn't exist already
    dirname = os.path.dirname(outfile)
    make_sure_path_exists(dirname)

    # Skip the file if it already exists
    if skip_if_file_exists and os.path.exists(outfile):
        logger.debug('File %s already exists, skipping', outfile)
        return

    # Just copy over binary files. Don't render.
    logger.debug("Check %s to see if it's a binary", infile)
    if is_binary(infile):
        logger.debug('Copying binary %s to %s without rendering', infile, outfile)
        shutil.copyfile(infile, outfile)
    else:
        # Force fwd slashes on Windows for get_template
        # This is a by-product of the Python cross-platform support.
        infile_fwd_slashes = infile.replace(os.path.sep, '/')
        try:
            # Render the file
            template = env.get_template(infile_fwd_slashes)
            rendered_file = template.render(**context)

            # Write it to the corresponding place in the output dir
            logger.debug('Writing %s to %s', infile, outfile)

            with open(outfile, 'w', encoding='utf-8') as fh:
                fh.write(rendered_file)

        except (TemplateSyntaxError, UndefinedError) as err:
            msg = f"Encountered error while rendering template: {err}"
            raise UndefinedVariableInTemplate(msg, err, context)

def render_and_create_dir(dirname: str, context: dict, output_dir: 'os.PathLike[str]', environment: Environment, overwrite_if_exists: bool=False):
    """Render name of a directory, create the directory, return its path."""
    name_tmpl = environment.from_string(dirname)
    rendered_dirname = name_tmpl.render(**context)
    dir_to_create = os.path.normpath(os.path.join(output_dir, rendered_dirname))

    logger.debug('Rendered dir %s must exist in output_dir %s', dir_to_create, output_dir)

    if os.path.exists(dir_to_create):
        if overwrite_if_exists:
            logger.debug('Overwriting %s', dir_to_create)
        else:
            logger.debug('Dir %s already exists', dir_to_create)
            raise OutputDirExistsException(dir_to_create)

    make_sure_path_exists(dir_to_create)
    return dir_to_create

def _run_hook_from_repo_dir(repo_dir, hook_name, project_dir, context, delete_project_on_failure):
    """Run hook from repo directory, clean project directory if hook fails.

    :param repo_dir: Project template input directory.
    :param hook_name: The hook to execute.
    :param project_dir: The directory to execute the script from.
    :param context: Cookiecutter project context.
    :param delete_project_on_failure: Delete the project directory on hook
        failure?
    """
    with work_in(repo_dir):
        try:
            run_hook(hook_name, project_dir, context)
        except FailedHookException:
            if delete_project_on_failure:
                logger.debug(
                    'Hook %s failed. Deleting project directory %s',
                    hook_name,
                    project_dir,
                )
                rmtree(project_dir)
            raise

def generate_files(repo_dir, context=None, output_dir='.', overwrite_if_exists=False, skip_if_file_exists=False, accept_hooks=True, keep_project_on_failure=False):
    """Render the templates and saves them to files.

    :param repo_dir: Project template input directory.
    :param context: Dict for populating the template's variables.
    :param output_dir: Where to output the generated project dir into.
    :param overwrite_if_exists: Overwrite the contents of the output directory
        if it exists.
    :param skip_if_file_exists: Skip the files in the corresponding directories
        if they already exist
    :param accept_hooks: Accept pre and post hooks if set to `True`.
    :param keep_project_on_failure: If `True` keep generated project directory even when
        generation fails
    """
    context = context or {}
    env = create_env_with_context(context)

    project_dir = render_and_create_dir(
        context['cookiecutter']['_template'],
        context,
        output_dir,
        env,
        overwrite_if_exists
    )

    # We want the Jinja path and the OS paths to match. Consequently, we'll:
    #   + CD to the repo directory
    #   + Walk the `template_dir` directory and construct paths to each file
    #     relative to `template_dir`
    #   + Construct absolute paths to each file
    #   + Generate the files to the desired output directory

    repo_dir_path = os.path.abspath(repo_dir)
    with work_in(repo_dir_path):
        for root, dirs, files in os.walk('.'):
            for dirname in dirs:
                dirpath = os.path.normpath(os.path.join(root, dirname))
                try:
                    render_and_create_dir(
                        dirpath, context, project_dir, env, overwrite_if_exists
                    )
                except UndefinedError as err:
                    msg = f"Unable to create directory '{dirpath}': {err}"
                    raise UndefinedVariableInTemplate(msg, err, context)

            for filename in files:
                infile = os.path.normpath(os.path.join(root, filename))
                if is_copy_only_path(infile, context):
                    outfile_tmpl = env.from_string(infile)
                    outfile_rendered = outfile_tmpl.render(**context)
                    outfile = os.path.join(project_dir, outfile_rendered)
                    logger.debug('Copying %s to %s without rendering', infile, outfile)
                    shutil.copyfile(infile, outfile)
                else:
                    try:
                        generate_file(project_dir, infile, context, env, skip_if_file_exists)
                    except UndefinedError as err:
                        if delete_project_on_failure:
                            rmtree(project_dir)
                        raise UndefinedVariableInTemplate(
                            f"Unable to create file '{infile}': {err}",
                            err,
                            context
                        )

    if accept_hooks:
        _run_hook_from_repo_dir('post_gen_project', repo_dir, project_dir, context, not keep_project_on_failure)

    return project_dir
