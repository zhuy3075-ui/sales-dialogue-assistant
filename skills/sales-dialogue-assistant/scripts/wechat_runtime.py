"""Private runtime helpers for the read-only WeChat/ChatLab integration."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SKILL = Path(__file__).resolve().parents[1]
VERSION = '2.8.0'
DEFAULT_RUNTIME = Path.home()/'.sales-dialogue-assistant/runtime'/('wechat-'+VERSION)
DEFAULT_HOME = Path.home()/'.sales-dialogue-assistant/wechat'


class IntegrationError(Exception):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code, self.details = code, details


def private_dir(value):
    path = Path(value).expanduser().resolve()
    if path == SKILL or SKILL in path.parents:
        raise IntegrationError('PRIVATE_PATH_REQUIRED', '运行时和聊天数据必须放在技能包外')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.writing-', suffix='.tmp', delete=False) as f:
        temp = Path(f.name)
        json.dump(value, f, ensure_ascii=False, indent=2)
    try:
        if os.name != 'nt': temp.chmod(0o600)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def identifier(value):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', value):
        raise IntegrationError('INVALID_ACCOUNT', '账号配置名只用字母、数字、横线和下划线，最多64位')
    if value.upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        raise IntegrationError('INVALID_ACCOUNT', '账号配置名为系统保留字')
    return value


def runtime_info(path=None):
    root = Path(path or os.environ.get('SALES_WECHAT_RUNTIME', DEFAULT_RUNTIME)).expanduser().resolve()
    file = root/'runtime.json'
    if not file.is_file():
        raise IntegrationError('NOT_INSTALLED', '请先运行 scripts/setup_wechat.py')
    config = read_json(file)
    for name in ('python','node','clb'):
        if not Path(config[name]).is_file():
            raise IntegrationError('RUNTIME_MISSING', f'{name}文件缺失，请重新运行安装器')
    return root, config


def run(command, *, env=None, timeout=120, json_output=True, cwd=None):
    try:
        result = subprocess.run([str(x) for x in command], env=env, cwd=cwd, capture_output=True,
                                encoding='utf-8', errors='replace', timeout=timeout, shell=False)
    except subprocess.TimeoutExpired:
        raise IntegrationError('CLI_TIMEOUT', '本地CLI超时，未自动重复执行')
    if result.returncode:
        # Do not leak raw scanner output, secrets, or arbitrary conversation text on failure.
        diagnostic = result.stderr + result.stdout
        if '多个微信进程' in diagnostic or 'Specify --pid' in diagnostic:
            raise IntegrationError('PROCESS_AMBIGUOUS', '请先明确选择对应的微信进程，再用--pid初始化；没有自动扩大扫描范围')
        if 'denied process access' in diagnostic:
            raise IntegrationError('PROCESS_ACCESS_DENIED', '系统未允许读取该微信进程；未修改权限或签名，可使用已有配置或导出的聊天')
        raise IntegrationError('CLI_FAILED', '本地CLI执行失败；请先运行doctor检查依赖和账号配置', exit_code=result.returncode)
    if not json_output:
        return result.stdout.strip()
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise IntegrationError('INVALID_CLI_OUTPUT', 'CLI未返回可解析JSON，没有把报错当聊天内容')
    if isinstance(value, dict) and value.get('ok') is False:
        raise IntegrationError('CLI_REJECTED', 'CLI拒绝本次操作', upstream_code=value.get('error',{}).get('code'))
    return value


def cli_env(home, state=None):
    env = dict(os.environ)
    # Keep ChatLab config/history isolated as well as its database directory.
    sandbox = private_dir(Path(home)/'chatlab-user')
    env.update(HOME=str(sandbox), USERPROFILE=str(sandbox),
               CHATLAB_DATA_DIR=str(Path(home)/'chatlab-data'),
               CHATLAB_SKIP_UPDATE_CHECK='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
               PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONPATH', None)
    if state:
        env['WECHAT_CLI_STATE_DIR'] = str(state)
    return env


def call_wechat(runtime, home, config_file, args):
    config_file = Path(config_file).resolve()
    env = cli_env(home, config_file.parent)
    return run([runtime['python'], '-B', '-X', 'utf8', '-m', 'wechat_cli.main',
                '--config', config_file, *args], env=env)


def call_chatlab(runtime, home, args, timeout=120):
    return run([runtime['node'], runtime['clb'], *args], env=cli_env(home), timeout=timeout)


def session_id(account, username):
    return 'wechat-'+hashlib.sha256((account+'\0'+username).encode()).hexdigest()[:28]


def emit(value):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(value, ensure_ascii=False, indent=2))
