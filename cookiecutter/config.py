"""Global configuration handling."""
import collections
import copy
import logging
import os
import yaml
from cookiecutter.exceptions import ConfigDoesNotExistException, InvalidConfiguration
logger = logging.getLogger(__name__)
USER_CONFIG_PATH = os.path.expanduser('~/.cookiecutterrc')
BUILTIN_ABBREVIATIONS = {'gh': 'https://github.com/{0}.git', 'gl': 'https://gitlab.com/{0}.git', 'bb': 'https://bitbucket.org/{0}'}
DEFAULT_CONFIG = {'cookiecutters_dir': os.path.expanduser('~/.cookiecutters/'), 'replay_dir': os.path.expanduser('~/.cookiecutter_replay/'), 'default_context': collections.OrderedDict([]), 'abbreviations': BUILTIN_ABBREVIATIONS}

def _expand_path(path):
    """Expand both environment variables and user home in the given path."""
    return os.path.expandvars(os.path.expanduser(path))

def merge_configs(default, overwrite):
    """Recursively update a dict with the key/value pair of another.

    Dict values that are dictionaries themselves will be updated, whilst
    preserving existing keys.
    """
    merged = copy.deepcopy(default)
    for k, v in overwrite.items():
        if isinstance(v, collections.abc.Mapping):
            merged[k] = merge_configs(merged.get(k, {}), v)
        else:
            merged[k] = v
    return merged

def get_config(config_path):
    """Retrieve the config from the specified path, returning a config dict."""
    if not os.path.exists(config_path):
        raise ConfigDoesNotExistException(f"Config file {config_path} does not exist.")

    with open(config_path) as file_handle:
        try:
            config_dict = yaml.safe_load(file_handle)
        except yaml.YAMLError as e:
            raise InvalidConfiguration(f"Unable to parse YAML file {config_path}: {e}")

    config_dict['config_file'] = config_path

    return config_dict

def get_user_config(config_file=None, default_config=False):
    """Return the user config as a dict.

    If ``default_config`` is True, ignore ``config_file`` and return default
    values for the config parameters.

    If ``default_config`` is a dict, merge values with default values and return them
    for the config parameters.

    If a path to a ``config_file`` is given, that is different from the default
    location, load the user config from that.

    Otherwise look up the config file path in the ``COOKIECUTTER_CONFIG``
    environment variable. If set, load the config from this path. This will
    raise an error if the specified path is not valid.

    If the environment variable is not set, try the default config file path
    before falling back to the default config values.
    """
    if default_config is True:
        return copy.deepcopy(DEFAULT_CONFIG)

    if isinstance(default_config, dict):
        return merge_configs(DEFAULT_CONFIG, default_config)

    if config_file and config_file != USER_CONFIG_PATH:
        return get_config(config_file)

    user_config = os.environ.get('COOKIECUTTER_CONFIG')
    if user_config:
        return get_config(user_config)

    if os.path.exists(USER_CONFIG_PATH):
        return get_config(USER_CONFIG_PATH)

    return copy.deepcopy(DEFAULT_CONFIG)
