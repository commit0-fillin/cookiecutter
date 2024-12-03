"""Functions for prompting the user for project info."""
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path
from jinja2.exceptions import UndefinedError
from rich.prompt import Confirm, InvalidResponse, Prompt, PromptBase
from cookiecutter.exceptions import UndefinedVariableInTemplate
from cookiecutter.utils import create_env_with_context, rmtree

def read_user_variable(var_name, default_value, prompts=None, prefix=''):
    """Prompt user for variable and return the entered value or given default.

    :param str var_name: Variable of the context to query the user
    :param default_value: Value that will be returned if no input happens
    """
    prompt = f"{prefix}{var_name}"
    if prompts and var_name in prompts:
        prompt = prompts[var_name]
    
    user_value = Prompt.ask(prompt, default=str(default_value))
    return user_value if user_value else default_value

class YesNoPrompt(Confirm):
    """A prompt that returns a boolean for yes/no questions."""
    yes_choices = ['1', 'true', 't', 'yes', 'y', 'on']
    no_choices = ['0', 'false', 'f', 'no', 'n', 'off']

    def process_response(self, value: str) -> bool:
        """Convert choices to a bool."""
        value = value.lower()
        if value in self.yes_choices:
            return True
        elif value in self.no_choices:
            return False
        else:
            raise InvalidResponse(self.validate_error_message)

def read_user_yes_no(var_name, default_value, prompts=None, prefix=''):
    """Prompt the user to reply with 'yes' or 'no' (or equivalent values).

    - These input values will be converted to ``True``:
      "1", "true", "t", "yes", "y", "on"
    - These input values will be converted to ``False``:
      "0", "false", "f", "no", "n", "off"

    Actual parsing done by :func:`prompt`; Check this function codebase change in
    case of unexpected behaviour.

    :param str question: Question to the user
    :param default_value: Value that will be returned if no input happens
    """
    prompt = f"{prefix}{var_name}"
    if prompts and var_name in prompts:
        prompt = prompts[var_name]
    
    return YesNoPrompt.ask(prompt, default=default_value)

def read_repo_password(question):
    """Prompt the user to enter a password.

    :param str question: Question to the user
    """
    return Prompt.ask(question, password=True)

def read_user_choice(var_name, options, prompts=None, prefix=''):
    """Prompt the user to choose from several options for the given variable.

    The first item will be returned if no input happens.

    :param str var_name: Variable as specified in the context
    :param list options: Sequence of options that are available to select from
    :return: Exactly one item of ``options`` that has been chosen by the user
    """
    prompt = f"{prefix}{var_name}"
    if prompts and var_name in prompts:
        prompt = prompts[var_name]
    
    choices = {str(i): option for i, option in enumerate(options, 1)}
    choice_prompt = f"{prompt}\n" + "\n".join(f"{k}: {v}" for k, v in choices.items())
    
    while True:
        choice = Prompt.ask(choice_prompt, default="1")
        if choice in choices:
            return choices[choice]
        print("Invalid choice. Please try again.")
DEFAULT_DISPLAY = 'default'

def process_json(user_value, default_value=None):
    """Load user-supplied value as a JSON dict.

    :param str user_value: User-supplied value to load as a JSON dict
    """
    try:
        return json.loads(user_value)
    except json.JSONDecodeError:
        return default_value

class JsonPrompt(PromptBase[dict]):
    """A prompt that returns a dict from JSON string."""
    default = None
    response_type = dict
    validate_error_message = '[prompt.invalid]  Please enter a valid JSON string'

    def process_response(self, value: str) -> dict:
        """Convert choices to a dict."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise InvalidResponse(self.validate_error_message)

def read_user_dict(var_name, default_value, prompts=None, prefix=''):
    """Prompt the user to provide a dictionary of data.

    :param str var_name: Variable as specified in the context
    :param default_value: Value that will be returned if no input is provided
    :return: A Python dictionary to use in the context.
    """
    prompt = f"{prefix}{var_name}"
    if prompts and var_name in prompts:
        prompt = prompts[var_name]
    
    default_json = json.dumps(default_value)
    user_value = JsonPrompt.ask(prompt, default=default_json)
    return user_value if user_value else default_value

def render_variable(env, raw, cookiecutter_dict):
    """Render the next variable to be displayed in the user prompt.

    Inside the prompting taken from the cookiecutter.json file, this renders
    the next variable. For example, if a project_name is "Peanut Butter
    Cookie", the repo_name could be be rendered with:

        `{{ cookiecutter.project_name.replace(" ", "_") }}`.

    This is then presented to the user as the default.

    :param Environment env: A Jinja2 Environment object.
    :param raw: The next value to be prompted for by the user.
    :param dict cookiecutter_dict: The current context as it's gradually
        being populated with variables.
    :return: The rendered value for the default variable.
    """
    if not isinstance(raw, str):
        return raw

    template = env.from_string(raw)
    try:
        return template.render(**cookiecutter_dict)
    except UndefinedError as err:
        raise UndefinedVariableInTemplate(str(err), err, cookiecutter_dict)

def _prompts_from_options(options: dict) -> dict:
    """Process template options and return friendly prompt information."""
    prompts = {}
    for key, value in options.items():
        if isinstance(value, dict):
            if 'prompt' in value:
                prompts[key] = value['prompt']
            elif 'description' in value:
                prompts[key] = value['description']
    return prompts

def prompt_choice_for_template(key, options, no_input):
    """Prompt user with a set of options to choose from.

    :param no_input: Do not prompt for user input and return the first available option.
    """
    if no_input:
        return next(iter(options.values()))

    choices = list(options.keys())
    choice_map = {str(i): choice for i, choice in enumerate(choices, 1)}
    choice_lines = [f"{i}: {choice}" for i, choice in choice_map.items()]
    prompt = f"\nSelect {key}:\n" + "\n".join(choice_lines)

    while True:
        choice = Prompt.ask(prompt, default="1")
        if choice in choice_map:
            return options[choice_map[choice]]
        print("Invalid choice. Please try again.")

def prompt_choice_for_config(cookiecutter_dict, env, key, options, no_input, prompts=None, prefix=''):
    """Prompt user with a set of options to choose from.

    :param no_input: Do not prompt for user input and return the first available option.
    """
    rendered_options = OrderedDict()
    for option_key, option_value in options.items():
        rendered_options[option_key] = render_variable(env, option_value, cookiecutter_dict)

    if no_input:
        return next(iter(rendered_options.values()))

    prompt = f"{prefix}{key}"
    if prompts and key in prompts:
        prompt = prompts[key]

    return read_user_choice(prompt, list(rendered_options.values()))

def prompt_for_config(context, no_input=False):
    """Prompt user to enter a new config.

    :param dict context: Source for field names and sample values.
    :param no_input: Do not prompt for user input and use only values from context.
    """
    cookiecutter_dict = OrderedDict([])
    env = create_env_with_context(context)

    prompts = _prompts_from_options(context.get('cookiecutter', {}))

    for key, raw in context.get('cookiecutter', {}).items():
        if not isinstance(raw, dict):
            val = render_variable(env, raw, cookiecutter_dict)
            if not no_input:
                val = read_user_variable(key, val, prompts)
        else:
            val = prompt_choice_for_config(
                cookiecutter_dict, env, key, raw, no_input, prompts
            )
        cookiecutter_dict[key] = val

    return cookiecutter_dict

def choose_nested_template(context: dict, repo_dir: str, no_input: bool=False) -> str:
    """Prompt user to select the nested template to use.

    :param context: Source for field names and sample values.
    :param repo_dir: Repository directory.
    :param no_input: Do not prompt for user input and use only values from context.
    :returns: Path to the selected template.
    """
    template_dir = Path(repo_dir)
    nested_templates = [d for d in template_dir.iterdir() if d.is_dir()]

    if not nested_templates:
        return repo_dir

    if no_input:
        return str(nested_templates[0])

    choices = {str(i): str(template) for i, template in enumerate(nested_templates, 1)}
    choice_lines = [f"{i}: {template.name}" for i, template in choices.items()]
    prompt = "Select a nested template:\n" + "\n".join(choice_lines)

    while True:
        choice = Prompt.ask(prompt, default="1")
        if choice in choices:
            return choices[choice]
        print("Invalid choice. Please try again.")

def prompt_and_delete(path, no_input=False):
    """
    Ask user if it's okay to delete the previously-downloaded file/directory.

    If yes, delete it. If no, checks to see if the old version should be
    reused. If yes, it's reused; otherwise, Cookiecutter exits.

    :param path: Previously downloaded zipfile.
    :param no_input: Suppress prompt to delete repo and just delete it.
    :return: True if the content was deleted
    """
    # Suppress prompt if called with no_input
    if no_input:
        rmtree(path)
        return True

    delete = YesNoPrompt.ask(
        f"You've downloaded {path} before. Is it okay to delete and re-download it?",
        default=True
    )

    if delete:
        rmtree(path)
        return True

    reuse = YesNoPrompt.ask(
        "Do you want to re-use the existing version?",
        default=True
    )

    if reuse:
        return False

    sys.exit()
