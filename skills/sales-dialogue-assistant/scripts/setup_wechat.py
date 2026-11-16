"""Install isolated dependencies, select the native platform and run first-use tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import venv
import zipfile

from wechat_runtime import (DEFAULT_HOME, DEFAULT_RUNTIME, SKILL, VERSION, IntegrationError,
                           emit, private_dir, read_json, write_json)

CHATLAB = '0.37.7'
NODE = '24.11.1'
PYTHON_REQUIREMENTS = ['click==8.3.1','pycryptodome==3.23.0','zstandard==0.25.0']


def select_platform(system=None, machine=None):
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    arch = {'amd64':'x64','x86_64':'x64','aarch64':'arm64','arm64':'arm64'}.get(machine)
    os_id = {'Windows':'win','Darwin':'darwin','Linux':'linux'}.get(system)
    if not arch or not os_id:
        raise IntegrationError('UNSUPPORTED_PLATFORM', f'未支持 {system}/{machine}，可改用导出的聊天文本')
    return {'os':system,'arch':arch,'node_platform':os_id,
            'scanner':{'Windows':'windows','Darwin':'macos','Linux':'linux'}[system],
            'is_host_platform':system==platform.system() and machine==platform.machine().lower()}


def execute(command, root, label, env=None, timeout=900):
    # Logs belong to this user's runtime, never the distributable package.
    log = root/'logs'/(label+'.log')
    log.parent.mkdir(parents=True,exist_ok=True)
    print(label+'…', file=sys.stderr, flush=True)
    with log.open('w',encoding='utf-8') as output:
        result = subprocess.run([str(x) for x in command], env=env, stdout=output,
                                stderr=subprocess.STDOUT, timeout=timeout, shell=False)
    if result.returncode:
        raise IntegrationError('INSTALL_STEP_FAILED', f'{label}失败；保留现有文件，未标为安装成功',log=str(log),exit_code=result.returncode)


def fetch(url, path):
    request = urllib.request.Request(url,headers={'User-Agent':'sales-dialogue-assistant/'+VERSION})
    with urllib.request.urlopen(request,timeout=90) as response, Path(path).open('wb') as output:
        shutil.copyfileobj(response,output)


def node_runtime(root, target):
    existing = shutil.which('node')
    if existing:
        version = subprocess.check_output([existing,'--version'],text=True).strip()
        nums = tuple(map(int,re.findall(r'\d+',version)[:3]))
        if nums >= (22,19,0) and nums[0] % 2 == 0:
            return str(Path(existing).resolve()),version
    folder = root/'node'; folder.mkdir(exist_ok=True)
    suffix = '.zip' if target['os']=='Windows' else '.tar.gz'
    name = f"node-v{NODE}-{target['node_platform']}-{target['arch']}"
    archive = folder/(name+suffix)
    base = f'https://nodejs.org/dist/v{NODE}/'
    sums = folder/'SHASUMS256.txt'
    fetch(base+'SHASUMS256.txt',sums)
    entries = {line.split()[1]:line.split()[0] for line in sums.read_text().splitlines() if len(line.split())==2}
    expected = entries.get(archive.name)
    if not expected: raise IntegrationError('NODE_ASSET_UNAVAILABLE',f'官方未列出当前平台文件：{archive.name}')
    fetch(base+archive.name,archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:
        raise IntegrationError('CHECKSUM_MISMATCH','Node下载校验失败，不执行文件')
    if suffix=='.zip':
        with zipfile.ZipFile(archive) as source:
            for entry in source.infolist():
                if not (folder.resolve() in (folder/entry.filename).resolve().parents):
                    raise IntegrationError('ARCHIVE_PATH','下载包存在越界路径')
            source.extractall(folder)
        node = folder/name/'node.exe'
    else:
        with tarfile.open(archive) as source:
            if hasattr(tarfile, 'data_filter'):
                source.extractall(folder,filter='data')
            else:
                raise IntegrationError('PYTHON_PATCH_TOO_OLD','安全解包需要更新的Python补丁版本；请用uv run --python 3.12运行安装器')
        node = folder/name/'bin/node'
    version = subprocess.check_output([str(node),'--version'],text=True).strip()
    return str(node.resolve()),version


def install(args):
    if sys.version_info < (3,10): raise IntegrationError('PYTHON_TOO_OLD','需要Python>=3.10，请通过install.ps1/install.sh启动')
    if os.name != 'nt': os.umask(0o077)
    root = private_dir(args.runtime)
    home = private_dir(args.home)
    target = select_platform()
    if args.plan:
        emit({'ok':True,'platform':target,'runtime':str(root),'python_dependencies':PYTHON_REQUIREMENTS,
              'chatlab':CHATLAB,'first_test':'isolated synthetic chat','real_chat':'requires selected account and friend'})
        return
    venv_dir = root/'python'
    previous = root/'runtime.json'
    if previous.is_file():
        state = read_json(previous)
        state['selftest'] = 'setup_in_progress'
        write_json(previous,state)
    python = venv_dir/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.is_file(): venv.EnvBuilder(with_pip=True).create(venv_dir)
    env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8', PIP_DISABLE_PIP_VERSION_CHECK='1', PYTHONNOUSERSITE='1')
    env.pop('PYTHONPATH',None)
    execute([python,'-m','pip','install','--only-binary=:all:',*PYTHON_REQUIREMENTS],root,'install-python-dependencies',env)
    vendor = SKILL/'vendor/wechat-cli'
    # Work on a runtime copy so builds never add binaries/metadata to the shared Skill.
    build = root/'wechat-source'
    shutil.copytree(vendor,build,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info','build'))
    if target['os']=='Darwin':
        cc = shutil.which('clang') or shutil.which('cc')
        if not cc: raise IntegrationError('MAC_COMPILER_MISSING','需要Apple命令行编译工具。请用户安装后重跑；未修改签名或系统权限')
        machine = 'arm64' if target['arch']=='arm64' else 'x86_64'
        binary = build/'wechat_cli/bin'/('find_all_keys_macos.'+machine)
        execute([cc,'-O2','-arch',machine,'-o',binary,build/'wechat_cli/bin/find_all_keys_macos.c','-framework','Foundation'],root,'compile-macos-scanner',env)
    execute([python,'-m','pip','install','--no-deps','--force-reinstall',build],root,'install-wechat-cli',env)
    node, version = node_runtime(root,target)
    npm_cli = Path(node).parent/'node_modules/npm/bin/npm-cli.js'
    if not npm_cli.exists(): npm_cli = Path(node).parent.parent/'lib/node_modules/npm/bin/npm-cli.js'
    if npm_cli.is_file(): npm = [node,str(npm_cli)]
    elif shutil.which('npm'): npm = [shutil.which('npm')]
    else: raise IntegrationError('NPM_MISSING','Node可用但npm缺失；请安装包含npm的Node LTS后重跑')
    npm_dir = root/'chatlab'
    npm_dir.mkdir(exist_ok=True)
    lock = SKILL/'assets/wechat-runtime/package-lock.json'
    if lock.is_file():
        shutil.copy2(lock,npm_dir/'package-lock.json')
        shutil.copy2(lock.with_name('package.json'),npm_dir/'package.json')
        command = npm+['ci','--prefix',str(npm_dir),'--no-audit','--no-fund']
    else:
        write_json(npm_dir/'package.json',{'name':'sales-wechat-runtime','version':VERSION,'private':True,'dependencies':{'chatlab-cli':CHATLAB}})
        command = npm+['install','--prefix',str(npm_dir),'--no-audit','--no-fund']
    env['PATH'] = str(Path(node).parent)+os.pathsep+env.get('PATH','')
    execute(command,root,'install-chatlab',env)
    clb = npm_dir/'node_modules/chatlab-cli/bin/chatlab.mjs'
    record = {'version':VERSION,'python':str(python),'node':node,'node_version':version,
              'clb':str(clb),'chatlab_version':CHATLAB,'platform':target,'selftest':'pending'}
    write_json(root/'runtime.json',record)
    execute([python,'-B',SKILL/'scripts/wechat_selftest.py','--runtime',root],root,'first-use-selftest',env,timeout=300)
    result = read_json(root/'selftest-result.json')
    if result.get('ok') is not True: raise IntegrationError('SELFTEST_FAILED','首次模拟自检没有通过')
    record['selftest'] = 'passed_synthetic'
    write_json(root/'runtime.json',record)
    emit({'ok':True,'state':'dependencies_and_synthetic_test_ready','version':VERSION,'platform':target,
          'runtime':str(root),'selftest':result,'real_account':'not_initialized_by_installer',
          'next':'指定微信账号；已有授权配置可绑定，否则首次密钥读取需用户明确同意。然后按好友昵称读取上下文。'})


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',default=str(DEFAULT_RUNTIME)); parser.add_argument('--home',default=str(DEFAULT_HOME))
    parser.add_argument('--plan',action='store_true')
    try: install(parser.parse_args())
    except IntegrationError as exc:
        emit({'ok':False,'error':{'code':exc.code,'message':str(exc),**exc.details}});sys.exit(2)
    except (OSError,subprocess.SubprocessError) as exc:
        emit({'ok':False,'error':{'code':'DEPENDENCY_SETUP_FAILED','message':str(exc)}});sys.exit(2)
