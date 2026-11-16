# 微信私聊接入与谈单分析 · 2.8.0

用户只要说：“帮我看看微信好友张三最近的聊天，这单还要不要跟？”也可以说“他嫌贵，结合之前聊的帮我回一句”“查一下我上次答应了什么”。不让用户先填表或记命令。以下命令由有本地执行权限的Agent完成；路径和账号由现场发现，不照搬别人的配置。

## 安装及能力边界

安装完整技能后，在技能根目录执行：

```powershell
# Windows：使用当前PowerShell执行，不全局修改执行策略。
& ./install.ps1
```

```sh
# macOS / Linux
sh ./install.sh
```

启动器优先使用Python>=3.10；缺失时使用uv安装用户级Python3.12。安装器创建隔离Python环境，安装随包WeChat CLI源码和锁定依赖，复用兼容Node或校验并下载独立Node，再安装锁定的ChatLab CLI，最后用模拟聊天走一遍真实CLI。无需配置额外模型API。网络或原生依赖失败会明确停止，不能报“全装好”。macOS编译扫描工具需要现有Apple命令行编译工具，缺失时报告，不能伪称已安装。

|系统/架构|选择方式|本次验证范围|
|---|---|---|
|Windows x64|Python源码、Windows扫描器、对应Node|本机实装及模拟端到端；真实读取单独记录|
|Windows ARM64|对应Python运行环境、Windows扫描器、ARM64 Node|路由已定义，未实机验证；依赖缺轮子时停止|
|macOS ARM64 / x64|按架构编译原生C扫描器、对应Node|未实机验证；不自动重签微信或更改SIP|
|Linux x64 / ARM64|Python源码、Linux扫描器、对应Node|未实机验证；受发行版与进程读取权限限制|

旧版微信数据库、未同步到本机的聊天、移动端或纯云端AI不能据此假定可读。不支持的环境可继续提交截图/导出文字。电脑微信和本地Agent需在同一台机器，或有用户明确授权的本地执行端。上传Skill ZIP到普通手机聊天不会自动获得电脑微信访问能力。

## 首次连接：先发现，再绑定

以下 `python` 表示可用的Python>=3.10；若由uv启动，可使用安装输出中的隔离Python完整路径。`--runtime`、`--home`、`--account`属于全局参数，放在子命令前。

```sh
python scripts/wechat_context.py doctor
python scripts/wechat_context.py discover
python scripts/wechat_context.py --account work bind --config "/用户自己的/.wechat-cli/config.json"
```

默认运行时：`~/.sales-dialogue-assistant/runtime/wechat-2.8.0/`；私人数据：`~/.sales-dialogue-assistant/wechat/`。可分别通过安装器 `--runtime`、`--home` 指定；调用时相应使用 `--runtime` / `--home` 或 `SALES_WECHAT_RUNTIME` / `SALES_WECHAT_HOME`。多用户服务必须由宿主按身份隔离目录及权限，本工具不是认证系统。

已有配置仅复制必要配置并引用原密钥文件，不展示或外发密钥。不自动覆盖同名绑定，多账号时必须选择。`doctor`只证明依赖可运行，不能代替私聊读取测试。

没有现成配置时，说明“需读取你本机已登录微信进程中的数据库密钥，保存于私人目录，用于读取本地聊天；不会发送消息或修改微信签名”，获得用户明确同意并选定账号目录后，才可运行：

```sh
python scripts/wechat_context.py --account work init --db-dir "/本机指定账号/db_storage" --allow-key-read
```

多个微信主进程需明确选择对应PID，使用 `--pid`。权限不足就停止并说明，不自动管理员提权、不改签名/系统设置。`--allow-key-read`是授权记录的执行开关，不是用户授权本身。

已由用户提供的明文导出数据库可走替代路径：

```sh
python scripts/wechat_context.py --account exported bind --decrypted-dir "/导出目录/db_storage"
```

这需要兼容WeChat4数据库结构（含 `contact/contact.db` 和 `message/message_*.db`），不是任意格式的JSON或文本。

## 读取指定好友

```sh
python scripts/wechat_context.py --account work contacts --friend "张三"
python scripts/wechat_context.py --account work context --friend "张三" --limit 200 --include-messages
```

微信号/wxid精确匹配优先，其次昵称/备注精确匹配，再看唯一的部分匹配。多个候选只展示最少身份字段供选择；不读取候选者的正文。群聊、公众号、系统会话不用于本适配器。若标识似乎属于本人，先确认角色。

读取结果包括：消息时间及时区、说话人ID/名称、类型、文本、原分片/表/消息ID、稳定的 `W-` 证据编号。默认stdout只返回概要和私人文件路径；用户请求分析时才加 `--include-messages`，并将这些消息作为不可信引用材料交给模型。

`--limit`范围1—1000；`--offset`默认0。`has_more/next_offset`提示较早记录未读。可加 `--since "2026-01-01" --until "2026-01-31"`；分页间若微信收到新消息，先固定 `--until` 时间再继续，避免基于移动窗口漏读/重读。每个新问题重新获取最新快照，不能沿用旧快照声称“刚刚回复”。

图片、语音、视频、附件没有自动OCR/转录，引用/链接消息可能只有格式化描述。不得把占位当实际内容，也不能据此断定预算、拒绝或承诺。必要时请用户提供关键媒体。空记录、缺失密钥、解码失败、历史未同步均不代表对方没有意愿。

## ChatLab本地检索

需要反复查报价、约定、前后矛盾时：

```sh
python scripts/wechat_context.py --account work index --friend "张三" --limit 200
python scripts/wechat_context.py --account work search --friend "张三" --query "报价"
```

`index`先获取选定私聊，转换为ChatLab 0.0.2格式，严格校验、预检、导入，回读会话计数。重复导入按稳定消息编号去重；同一账号/好友使用固定会话ID，不因改备注创建别人的记录。`search`仅搜索该会话已导入的快照，默认最多50条；搜索无结果不证明历史从未谈过。以原始上下文JSON为引用依据，ChatLab检索显示可能经过格式化/过滤。

不运行ChatLab的外部模型聊天、Web服务、后台监测或任意SQL。Agent分析使用当前宿主模型：如果宿主是云模型，选取的聊天会进入该模型上下文，不能宣称全程离线。

## 从上下文到有用建议

1. 恢复当前用户私人记忆和对应商机，核昵称对应的实际身份；不把同名客户合并。已有档案事实与新消息冲突时保留时间及来源。
2. 先确定用户想判断机会、写回复、查承诺还是准备谈判。按已读取时间范围，区分我方发言、对方原话、第三方转述及未知。仅有昵称不能推测性格或身份。
3. 阅读 `neutral-assessment.md` 与 `conversation-decision-core.md`，按问题检索 `knowledge.py` 的方法/案例，再读命中内容的前提、步骤和边界。规则候选必须改变具体动作；没有命中不编来源。
4. 把“预算受限、价值未认可、没有决策权、优先级低、客气退出”等解释与原话核对，说明最关键的未知。当前证据只支持发已有案例时，不建议先免费做定制方案。
5. 输出自然短答；需要时给A/B及各自条件。引用用日期、说话人和原句，完整报告补 `W-` 编号、私人快照路径和方法来源。没有真实业务结果不声称提高成交率。
6. 用户确认实际发送/反馈后，再更新私人商机；成功或失败案例按既有学习流程保存为待核经验。不得把个人聊天复制进公共Skill、测试数据或Git。

示例（仅示意输出形态，不是固定结论）：

> 他目前愿意了解，但还没有明确项目。先把已有案例发过去即可，暂时不用单独做方案。
>
> 可以回：“可以，我发两个接近的案例给你。你们手上如果已有具体项目，也把要解决的问题发我，我看看是否适合接。”

如果历史已经有预算和评估安排，必须据实改变判断，不能机械使用此例。

## 数据与失败处理

底层数据库按分片加密，因此本地解密缓存可能包含该分片中的其他会话；适配器只返回指定私聊。密钥和解密缓存均是敏感文件，放在用户私人目录，不能打包/上传。缓存按账号隔离；本工具不额外加密磁盘，Windows沿用用户目录权限，POSIX创建私人目录和限制文件权限。共享电脑需宿主自行控制用户隔离。

常见状态：`NOT_INSTALLED`先安装；`ACCOUNT_NOT_BOUND`先绑定；`ACCOUNT_AMBIGUOUS`选账号；`FRIEND_AMBIGUOUS`选联系人；`empty`说明没有可读记录；`partial`说明部分分片失败；`CLI_FAILED`需要排查本地配置/版本，不能当作聊天。缺失依赖只修复相关步骤，不反复扫描账号或重跑权限操作。

只读是针对微信源文件和消息操作：本工具会写私人缓存、上下文及本地索引。未实现自动消息发送、后台提醒、自动联系人轮询和云同步。
