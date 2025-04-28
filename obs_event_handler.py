import json
import subprocess
import uuid
import yaml
from urllib.parse import unquote

import tornado.concurrent
import tornado.httpclient
import tornado.ioloop
import tornado.options
import tornado.web
from tornado import gen, concurrent
from tornado.options import define, options

define("port", default=1919, help="run on the given port", type=int)

HTTP_ACCEPT = 202
HTTP_BAD_REQUEST = 400


def check_data(data) -> bool:
    if data:
        json_data = json.loads(data)
        if json_data:
            return "subject" in json_data and json_data["subject"] != ""
    return False


class OBSEventHandler(tornado.web.RequestHandler):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    def archive_file_handler(self, file_path):
        orig_file_name = file_path.split('/')[-1]
        # 获取类型
        # 规范来讲应该通过文件头等方式确认，但考虑到内部使用就不做额外验证了
        suffix = orig_file_name.split('.')[-1]
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
            print('Not Archive! Skipping...')
            return

        print(subprocess.call(
            f'cd {self.temp_path} && {unzip_tool} {params} {orig_file_name}',
            shell=True))

    def send_400_response(self):
        bad_ret = {
            "code": HTTP_BAD_REQUEST,
            "data": {
                "msg": "Required field not in request body!",
            }
        }
        self.set_status(400)
        self.write(json.dumps(bad_ret))
        self.set_header('Content-Type', 'application/json')

    @gen.coroutine
    def post(self):
        if not check_data(self.request.body):
            self.send_400_response()
            return
        print(self.request.remote_ip)
        print(unquote(self.request.body.decode('utf-8')))
        success_ret = {
            "code": HTTP_ACCEPT,
            "data": {
                "msg": "create job success!",
                "job_id": uuid.uuid4().hex,
            }
        }
        self.handle_zip_file(self.request.body)
        self.set_status(202)
        self.write(json.dumps(success_ret))
        self.set_header('Content-Type', 'application/json')

    @tornado.concurrent.run_on_executor
    def handle_zip_file(self, datas):
        # datas 为 bytes
        req = json.loads(datas)
        obs_orig_file = req['subject']
        # 解码 HTTP 编码
        obs_file = unquote(obs_orig_file)
        print(f'{obs_file} upload detected!')
        print(f'Downloading {obs_file}...')
        result = subprocess.call(['obsutil', 'cp', f'obs://{self.bucket_name}/{obs_file}', self.temp_path])
        if result != 0:
            print(f'Error: {result}')

        print(subprocess.call(['ls', self.temp_path]))

        # Unzip
        print('Handle the Archive...')
        self.archive_file_handler(obs_file)
        print('Unpack Step Complete!')

        print(subprocess.call(['ls', self.temp_path]))

        # Move VPKs
        print('Moving VPKs...')
        vpks = subprocess.run(
            f'ls {self.temp_path} | grep vpk',
            shell=True, capture_output=True).stdout
        print('vpks:\n', vpks.decode('utf-8'))
        vpk_files = vpks.decode('utf-8').strip().split('\n')
        subprocess.call(
            f'mv {self.temp_path}/*.vpk {self.addon_path}',
            shell=True)
        print('Moved VPKs!')
        for vpk_file in vpk_files:
            chk_rst = subprocess.run(
                f'ls {self.addon_path}"{vpk_file}"',
                shell=True, capture_output=True)
            print(chk_rst.stdout.decode('utf-8'))

    def load_config_from_file(self):
        with open('config/config.yaml', 'r') as stream:
            config = yaml.safe_load(stream)
            self.addon_path = config['l4d2server']['addon_path']
            self.temp_path = config['l4d2server']['temp_path']
            self.bucket_name = config['l4d2server']['bucket_name']


urls = [(r'/', OBSEventHandler), ]


def main():
    tornado.options.parse_command_line()
    print('Listen at port:', options.port)
    app = tornado.web.Application(urls, debug=True)
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
