"""
    Author: @DZDcyj
    This module provides the basic structure of the http server for obs monitor
"""

import json
import logging
import threading
import uuid
from typing import Any
from urllib.parse import unquote

import tornado.httpclient
import tornado.ioloop
import tornado.options
import tornado.web
import yaml
from tornado import gen, concurrent
from tornado.httputil import HTTPServerRequest
from tornado.options import define, options
from tornado.web import Application

from common.common_method import execute_shell_command
from common.file_utils import file_extension_check, is_supported_file_type

define("port", default=1919, help="run on the given port", type=int)

HTTP_ACCEPT = 202
HTTP_BAD_REQUEST = 400
HTTP_CONFLICT = 409

logger = logging.getLogger(__name__)
lock = threading.Lock()


def check_data(data) -> bool:
    """
    This function check if the data is valid
    :param data: The post request data
    :return: If the data is valid
    """
    if data:
        json_data = json.loads(data)
        if json_data:
            return "subject" in json_data and json_data["subject"] != ""
    return False


# pylint: disable=W0223
class OBSEventHandler(tornado.web.RequestHandler):
    """
    The OBS HTTP Server Class
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    processing_files = []

    def __init__(self, application: "Application", request: HTTPServerRequest, **kwargs: Any):
        """
        The OBS HTTP Server Class initialization.
        :param application: Inherit from super class
        :param request: Inherit from super class
        :param kwargs: Inherit from super class
        """
        super().__init__(application, request, **kwargs)
        with open('config/config.yaml', 'r', encoding='utf-8') as stream:
            config = yaml.safe_load(stream)
            self.addons_path = config['l4d2server']['addons_path']
            self.temp_path = config['l4d2server']['temp_path']
            self.obs_bucket = config['l4d2server']['obs_bucket']

    def archive_file_handler(self, file_path):
        """
        Handle the Archive File
        :param file_path: The archive file path
        This function unzip the archive file of zip rar and 7z
        """
        orig_file_name = file_path.split('/')[-1]
        # 获取类型
        suffix = orig_file_name.split('.')[-1]
        if is_supported_file_type(suffix):
            logger.info('Check the file extension... Expected file extension: %s', suffix)
            # 通过文件头获取类型，仅支持 zip、7z、rar 和 vpk
            file_head_check_result, true_type = file_extension_check(f'{self.temp_path}/{orig_file_name}')
            if file_head_check_result:
                logger.info('File Head Check Success!')
            else:
                # 检测不一致时，以文件头为准选择解压缩命令
                logger.warning('File Head Check Failed. Expected File Type: %s, Got: %s', suffix, true_type)
                logger.info('Use %s as the real suffix', true_type)
                suffix = true_type
        else:
            logger.info('Not Supported File Type: %s', suffix)
        unzip_tool = ''
        params = ''
        if suffix == 'zip':
            unzip_tool = 'unzip'
            params = '-o'
        elif suffix == 'rar':
            unzip_tool = 'unrar'
            params = 'e -o+'
        elif suffix == '7z':
            unzip_tool = '7za'
            params = 'e -aoa'
        else:
            logger.info('Not Archive! Skipping...')
            return

        result = execute_shell_command(f'cd {self.temp_path} && {unzip_tool} {params} {orig_file_name}')
        logger.debug(result.stdout.decode('utf-8').strip())

    def send_400_response(self):
        """
        function that return 400 response
        """
        bad_ret = {
            "code": HTTP_BAD_REQUEST,
            "data": {
                "msg": "Required field not in request body!",
            }
        }
        self.set_status(HTTP_BAD_REQUEST)
        self.write(json.dumps(bad_ret))
        self.set_header('Content-Type', 'application/json')

    def send_409_response(self):
        """
        function that return 409 response
        """
        reflict_ret = {
            "code": HTTP_CONFLICT,
            "data": {
                "msg": "The file you requested is processing, please wait!",
            }
        }
        self.set_status(HTTP_CONFLICT)
        self.write(json.dumps(reflict_ret))
        self.set_header('Content-Type', 'application/json')

    def acquire_file_lock(self, file_name):
        """
        Acquire the lock for file to process.
        :param file_name: The file name
        :return: If the lock is acquired
        """
        with lock:
            logger.info('Acquire lock for %s success! Now Check File Status.', file_name)
            if file_name in self.processing_files:
                logger.info('%s is processing, abort!', file_name)
                return False
            self.processing_files.append(file_name)
            return True

    def release_file_lock(self, file_name):
        """
        Release the lock for file to process.
        :param file_name: The file name
        """
        with lock:
            logger.info('Release lock for %s success!', file_name)
            self.processing_files.remove(file_name)

    @gen.coroutine
    def post(self):
        """
        Main Function that handle the post requests
        """
        if not check_data(self.request.body):
            self.send_400_response()
            return
        logger.debug(self.request.remote_ip)
        logger.debug(unquote(self.request.body.decode('utf-8')))
        success_ret = {
            "code": HTTP_ACCEPT,
            "data": {
                "msg": "create job success!",
                "job_id": uuid.uuid4().hex,
            }
        }
        # datas 为 bytes
        req = json.loads(self.request.body)
        obs_orig_file = req['subject']
        # 解码 HTTP 编码
        obs_file = unquote(obs_orig_file)
        if not self.acquire_file_lock(obs_file):
            logger.info('File %s is processing, return 409!', obs_file)
            self.send_409_response()
            return
        self.handle_zip_file(self.request.body)
        self.set_status(202)
        self.write(json.dumps(success_ret))
        self.set_header('Content-Type', 'application/json')

    @concurrent.run_on_executor
    def handle_zip_file(self, datas):
        """
        This function handle the main process of archives handling
        :param datas: The post request body
        """
        # datas 为 bytes
        req = json.loads(datas)
        obs_orig_file = req['subject']
        # 解码 HTTP 编码
        obs_file = unquote(obs_orig_file)
        logger.info('%s upload detected!', obs_file)
        logger.info('Downloading %s...', obs_file)
        ret = execute_shell_command(f'obsutil cp obs://{self.obs_bucket}/{obs_file} {self.temp_path}')
        if ret.returncode != 0:
            logger.error('Error Occurred at Downloading Files: %s', obs_file)
            # 此处错误日志输出在 stdout
            logger.error('Error Info: %s', ret.stdout.decode('utf-8'))
            return

        result = execute_shell_command(f'ls {self.temp_path}').stdout.decode('utf-8').strip()
        files = ', '.join(result.split('\n'))
        logger.info('Files in %s: [%s]', self.temp_path, files)

        # Unzip
        logger.info('Handling the Archive...')
        self.archive_file_handler(obs_file)
        logger.info('Unpack Step Complete!')

        result = execute_shell_command(f'ls {self.temp_path}').stdout.decode('utf-8').strip()
        files = ', '.join(result.split('\n'))
        logger.info('Files in %s: [%s]', self.temp_path, files)

        # Move VPKs
        logger.info('Moving VPKs...')
        vpks = execute_shell_command(f'ls {self.temp_path} | grep vpk').stdout
        logger.info('Vpks in %s: [%s]', self.temp_path, ', '.join(vpks.decode('utf-8').strip().split('\n')))
        vpk_files = vpks.decode('utf-8').strip().split('\n')
        ret = execute_shell_command(f'mv {self.temp_path}/*.vpk {self.addons_path}')
        if ret.returncode != 0:
            logger.error('Error Occurred at Moving Files: %s', vpk_files)
            # 此处错误日志输出在 stderr
            logger.error('Error Info: %s', ret.stderr.decode('utf-8'))
        logger.info('Moved VPKs! Checking Existence...')
        all_success = True
        for vpk_file in vpk_files:
            chk_rst = execute_shell_command(f'ls {self.addons_path}/"{vpk_file}"')
            logger.debug(chk_rst.stdout.decode('utf-8'))
            if chk_rst.returncode != 0:
                all_success = False
                logger.error('Error Occurred at Check VPK: %s', vpk_file)
                logger.error('Error Info: %s', chk_rst.stderr.decode('utf-8'))

        if all_success:
            logger.info('All VPKs have been moved successfully!')
        self.release_file_lock(obs_file)


urls = [(r'/', OBSEventHandler), ]


def main():
    """
    The main function, starts the server
    """
    tornado.options.parse_command_line()
    logger.info('Listen at port: %s', options.port)
    app = tornado.web.Application(urls, debug=True)
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
