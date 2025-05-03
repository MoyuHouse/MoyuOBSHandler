"""
    Author: @DZDcyj
    This module provides the common functions.
"""
import subprocess


def execute_shell_command(command):
    """
    Executes a shell command and returns its output.
    :param command: The command to execute.
    :return: The output of the command.
    """
    return subprocess.run(command, shell=True, check=False, capture_output=True)
