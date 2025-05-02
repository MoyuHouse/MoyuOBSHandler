"""
    Author: @DZDcyj
    This module provides the file utility functions.
"""

import os

# 文件头对照表
TYPE_DICT = {
    "504B0304": "zip",  # ZIP file signature
    "52617221": "rar",  # RAR file signature
    "377ABCAF": "7z",  # 7z file signature
    "3412AA55": "vpk",  # vpk file signature
}

# 仅支持如下的文件头检测
SUPPORT_FILE_TYPE = ['zip', '7z', 'rar', 'vpk']


def bytes2hex(byte_array):
    """
    Converts a byte array to a hexadecimal string.
    :param byte_array: The byte array to convert.
    :return: Hexadecimal string representation of the byte array.
    """
    return ''.join(f"{byte:02X}" for byte in byte_array)


def get_file_type_by_file_head(file_path, output_file_head=False):
    """
    Returns the file type by reading file head. Now supports zip, rar, 7z, and vpk.
    :param file_path: The file path.
    :param output_file_head: If True, the file head will be printed.
    :return: The file type by reading file head.
    """
    file_type = 'unknown'
    with open(file_path, 'rb') as bin_file:
        # 读取文件头
        max_num_of_bytes = max(len(h_code) for h_code, _ in TYPE_DICT.items()) // 2
        header_bytes = bin_file.read(max_num_of_bytes)
        file_head_code = bytes2hex(header_bytes)

        # 对比文件头和记录的值
        for h_code, h_type in TYPE_DICT.items():
            if file_head_code.startswith(h_code):
                file_type = h_type
                break
    if output_file_head:
        print(file_head_code)
    return file_type


def file_extension_check(file_path, debug=False):
    """
    Checks if the given file has a correct file extension.
    :param file_path: The file with extension.
    :param debug: If True, the file extension will be printed.
    :return: A tuple containing:
        - A boolean indicating whether the file extension matches the file type.
        - The determined file type based on the file's header.
    """
    # 统一转小写判断
    file_extension = os.path.splitext(file_path)[1][1:].lower()
    file_head_extension = get_file_type_by_file_head(file_path, debug)
    return file_extension == file_head_extension, file_head_extension


def is_supported_file_type(file_type):
    """
    Checks if the given file type is supported.
    :param file_type: type of the file.
    :return: If the file type is supported, returns True.
    """
    return file_type in SUPPORT_FILE_TYPE


if __name__ == '__main__':
    # 测试用文件检测，debug 为 True 时打印文件头信息
    TEST_FILE = 'D:/SteamLibrary/steamapps/common/Left 4 Dead 2/left4dead2/addons/workshop/3421356207.vpk'
    print(file_extension_check(TEST_FILE, debug=True))
