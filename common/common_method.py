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
