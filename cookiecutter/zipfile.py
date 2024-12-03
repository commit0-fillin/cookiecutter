"""Utility functions for handling and fetching repo archives in zip format."""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from zipfile import BadZipFile, ZipFile
import requests
from cookiecutter.exceptions import InvalidZipRepository
from cookiecutter.prompt import prompt_and_delete, read_repo_password
from cookiecutter.utils import make_sure_path_exists

def unzip(zip_uri: str, is_url: bool, clone_to_dir: 'os.PathLike[str]'='.', no_input: bool=False, password: Optional[str]=None):
    """Download and unpack a zipfile at a given URI.

    This will download the zipfile to the cookiecutter repository,
    and unpack into a temporary directory.

    :param zip_uri: The URI for the zipfile.
    :param is_url: Is the zip URI a URL or a file?
    :param clone_to_dir: The cookiecutter repository directory
        to put the archive into.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :param password: The password to use when unpacking the repository.
    """
    clone_to_dir = Path(clone_to_dir)
    if is_url:
        # Download the file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            response = requests.get(zip_uri)
            temp_file.write(response.content)
            temp_file_path = temp_file.name
    else:
        temp_file_path = zip_uri

    # Create a temporary directory to extract the contents
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with ZipFile(temp_file_path) as zip_file:
                if password:
                    zip_file.setpassword(password.encode())
                zip_file.extractall(temp_dir)
        except BadZipFile:
            raise InvalidZipRepository(f"The file at {zip_uri} is not a valid zip file.")

        # Move the contents to the clone_to_dir
        extracted_contents = os.listdir(temp_dir)
        if len(extracted_contents) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_contents[0])):
            # If there's only one directory in the zip, use its contents
            source_dir = os.path.join(temp_dir, extracted_contents[0])
        else:
            # Otherwise, use all extracted contents
            source_dir = temp_dir

        destination = clone_to_dir / Path(zip_uri).stem
        if destination.exists():
            if no_input or prompt_and_delete(destination, no_input):
                shutil.rmtree(destination)
            else:
                return str(destination)

        shutil.copytree(source_dir, destination)

    if is_url:
        os.unlink(temp_file_path)

    return str(destination)
