"""应用上下文 — 单例持有配置、缓存、密钥等共享状态"""

import atexit
import json
import os

from .config import load_config, STATE_DIR
from .db_cache import DBCache
from .key_utils import strip_key_metadata
from .messages import find_msg_db_keys


class AppContext:
    """每次 CLI 调用初始化一次，被所有命令共享。"""

    def __init__(self, config_path=None):
        self.cfg = load_config(config_path)
        self.db_dir = self.cfg["db_dir"]
        self.decrypted_dir = self.cfg["decrypted_dir"]
        self.keys_file = self.cfg["keys_file"]

        if not self.cfg.get('plaintext') and not os.path.exists(self.keys_file):
            raise FileNotFoundError(
                f"密钥文件不存在: {self.keys_file}\n"
                "请运行: wechat-cli init"
            )

        if self.cfg.get('plaintext'):
            from pathlib import Path
            self.all_keys = {str(p.relative_to(self.db_dir)): {} for p in Path(self.db_dir).rglob('*.db')}
        else:
            with open(self.keys_file, encoding="utf-8") as f:
                self.all_keys = strip_key_metadata(json.load(f))

        self.cache = DBCache(self.all_keys, self.db_dir, self.cfg.get('cache_dir', os.path.join(os.path.dirname(self.keys_file), 'cache')), self.cfg.get('plaintext', False))
        atexit.register(self.cache.cleanup)

        self.msg_db_keys = find_msg_db_keys(self.all_keys)
        # A local shard without a key must be reported as missing coverage.
        from pathlib import Path
        actual = [str(p.relative_to(self.db_dir)).replace('\\', '/')
                  for p in Path(self.db_dir).glob('message/message_*.db')]
        self.msg_db_keys = find_msg_db_keys({k.replace('\\', '/'): {} for k in self.msg_db_keys + actual})

        # 确保状态目录存在
        os.makedirs(STATE_DIR, exist_ok=True)

    def display_name_fn(self, username, names):
        from .contacts import display_name_for_username
        return display_name_for_username(username, names, self.db_dir, self.cache, self.decrypted_dir)
