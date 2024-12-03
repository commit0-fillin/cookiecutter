"""
cookiecutter.replay.

-------------------
"""
import json
import os
from cookiecutter.utils import make_sure_path_exists

def get_file_name(replay_dir, template_name):
    """Get the name of file."""
    return os.path.join(replay_dir, f"{template_name}.json")

def dump(replay_dir: 'os.PathLike[str]', template_name: str, context: dict):
    """Write json data to file."""
    make_sure_path_exists(replay_dir)
    file_name = get_file_name(replay_dir, template_name)
    with open(file_name, 'w') as f:
        json.dump(context, f, indent=2)

def load(replay_dir, template_name):
    """Read json data from file."""
    file_name = get_file_name(replay_dir, template_name)
    if not os.path.exists(file_name):
        return None
    with open(file_name, 'r') as f:
        return json.load(f)
