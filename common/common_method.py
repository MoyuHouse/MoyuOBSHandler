"""
    Author: @DZDcyj
    This module provides the common functions.
"""
import subprocess


def execute_shell_command(command):
    """
    Executes a shell command and returns a CompletedProcess object.
    :param command: The command to execute.
    :return: A subprocess.CompletedProcess object containing the following attributes:
        - stdout: The standard output of the command.
        - stderr: The standard error of the command.
        - returncode: The return code of the command.
    """
    return subprocess.run(command, shell=True, check=False, capture_output=True)


def check_list_is_empty_or_whitespace_only(list_):
    """
    Checks if a list is empty or whitespace only.
    :param list_: The list to check.
    :return: If the list is empty or whitespace only.
    """
    return all(isinstance(item, str) and item.strip() == '' for item in list_)
