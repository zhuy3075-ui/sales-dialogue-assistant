# 谈单沟通助理 · Sales Dialogue Assistant

接收聊天、截图、报价单或一个想法，结合业务资料和谈单记录，帮助你判断客户意图、准备回复、讨论方案并持续跟进。

**当前版本：2.8.0 · 内测**。新增按微信好友昵称、备注或微信号读取本机私聊上下文，并可用ChatLab CLI检索已有报价和约定。默认按证据中性判断，回复自然、简短。技能需要由支持读取 Skill 文件的 AI 智能体执行，不是独立聊天应用，也不保证提高成交率。

## 适合谁

- 独立开发者、技术服务商：需求确认、定制开发报价、源码维护、范围变更、验收与回款沟通。
- 销售与商务人员：客户意图分析、内部采购沟通、合作筛选、谈判准备与复盘。
- 希望持续跟进客户的人：保留自己的表达偏好、业务条件和每笔交易的进展，减少反复介绍背景。

定制开发相关规程较完整；其他行业使用前，需要核实产品条件、交易规则及适用边界。

## 能帮你做什么

|任务|直接这样说|产出|
|---|---|---|
|读微信上下文|“看看微信里张三最近的聊天，这单该怎么推进？”|唯一匹配的私聊、带时间的依据、短回复和下一步|
|判断意图|“他这样说，到底在顾虑什么？”|有依据的解释、未知项和适当下一步|
|写回复|“这个怎么回？短一点，像微信聊天。”|一版结合上下文的回复草稿|
|看机会|“这单值不值得继续投入？”|按现有证据判断，区分交流意愿与实际采购动作|
|准备谈判|“明天见这个客户，帮我准备一下。”|目标、开场、关键问题、可能的回应与边界|
|生成材料|“整理成方案和报价，内部建议单独给我。”|依据同一组事实生成客户稿与内部说明|
|处理让步|“他要降价，给我两个谈法，别替我答应。”|条件不同的候选方案、取舍与退出条件|
|持续跟进|“接着上次那个客户，他又回复了。”|读取对应商机，恢复进展并更新实际反馈|
|陪练纠错|“你扮演客户，我试试怎么谈。”|明确标为模拟的练习和具体改句|
|积累经验|“这次我这样回，他约了演示，记一下。”|记录动作与反馈，经审核形成限定场景的经验|

## 快速开始

### 1. 获取完整技能目录

克隆当前内测分支：

```bash
git clone --branch pre-release https://github.com/zhuy3075-ui/sales-dialogue-assistant.git
cd sales-dialogue-assistant
```

也可以在 GitHub 页面选择 **Code → Download ZIP**，解压后找到：

```text
skills/sales-dialogue-assistant/
```

保留这个目录内的全部文件；只复制 `SKILL.md` 会丢失知识、模板和工具。仓库下载 ZIP 包含 README 等仓库文件，若平台要求上传技能 ZIP，应单独压缩 `skills/` 内的 `sales-dialogue-assistant` 文件夹。

### 2. 让你的 AI 帮你安装

把完整技能目录或技能 ZIP 交给支持文件操作的智能体，说：

> 帮我安装这个谈单沟通助理，把本机微信接入的依赖也装好并跑首次自检；有旧版先备份，保留我的私人记忆和客户记录。

宿主能管理本地技能时，可以按它的实际能力安装；只能聊天或只允许上传技能的平台，需要通过该平台提供的安装入口操作。**上传到普通聊天不等于已经安装，也不等于具备长期记忆。**

Codex 本地安装位置为 `$CODEX_HOME/skills/sales-dialogue-assistant`；未设置 `CODEX_HOME` 时为用户目录下的 `.codex/skills/sales-dialogue-assistant`。将技能文件夹完整复制到该位置；已有同名目录先备份。安装后新开会话，或让当前会话重新读取入口文件。

WorkBuddy、豆包、Claude 等宿主的安装入口、脚本执行和文件持久化能力需按当前环境核实，本项目未逐个平台实装验证。

有本地执行能力的Agent安装本包时，在技能根目录运行Windows的 `install.ps1` 或macOS/Linux的 `sh install.sh`。安装器会按系统/架构选择源码与运行时，建立隔离环境，安装WeChat CLI、ChatLab CLI及依赖，并用模拟聊天完成首次自检。已有授权的本机微信配置可直接绑定；首次读取登录进程的数据库密钥需要单独说明并取得同意。依赖装好、账号绑定、真实聊天可读分别验收，不自动提权或修改微信签名。

本轮实装平台为Windows x64；其他系统路由已实现，未实机验证。手机/纯云端AI仍可分析截图，但不能仅凭上传ZIP直接读取电脑微信。完整命令与限制见[微信接入指南](skills/sales-dialogue-assistant/references/wechat-context.md)。

### 3. 正常说话就能用

```text
用谈单沟通助理，帮我看看这段聊天。
```

Codex 中也可以明确调用：

```text
$sales-dialogue-assistant 他要我给案例，说转给负责人，你看我该投入多少时间？
```

截图能否识别取决于宿主模型的图像能力。看不清的姓名、数字、否定词等应补充文字，不能靠猜。

## 一个使用示例

**输入**

> 对方说：“我们有不少企业 AI 的订单，你给我案例，我转给负责人。”你看合作可能性怎么样？

**期望的回答方向（新拟演示）**

> 现在还看不出会不会给你单。他要案例转负责人，说明在了解你的能力，具体项目还没提。先发已有案例简介，看看能不能带回具体需求，暂时不为这条线索单独做方案。

如果后续出现明确项目、负责人参与和评估安排，判断应随证据变化。不会因为用户乐观就断定能成，也不会因为用户怀疑对方是中介就认定没戏。

示例不是固定话术，也不是实际成交证明。普通模型可能同样答好；本 Skill 的价值需要通过资料使用、事实连续性和具体决策来检验。

## 记忆与私人工作区

用户授权后，可分别保存：

|文件|用途|
|---|---|
|`ASSISTANT_MEMORY.md`|助手定位、协作约定、表达习惯与真实能力限制|
|`USER_MEMORY.md`|用户确认的目标、习惯和偏好|
|`BUSINESS.md`|范围、报价依据、维护、付款验收及让步权限|
|`deals/<id>.md`|每笔交易的事实、事件、承诺和待办|
|`artifacts/<id>.md`|带事实引用和版本依赖的工作草稿|
|`history/`|更新前的记录，供核查变更|

单用户本地默认工作区：

```text
~/.sales-dialogue-assistant/workspaces/default/
```

可通过 `SALES_ASSISTANT_WORKSPACE` 环境变量，或工具的 `--workspace` 参数指定其他位置。**工作区应放在仓库和技能包之外。** 多用户服务需由宿主按已认证身份分别绑定目录和访问权限；这个文件工具不是身份认证或加密系统。

你可以说：

> 记住，微信回复短一点，正式方案写完整。

> 看看你记了我的哪些习惯，这条改一下。

> 接着上次那个客户，我们上次停在哪里？

没有文件读写能力时，可导出两份 Markdown 记忆供下次带回。不同设备、平台不会自动同步；没有后台提醒或自动发消息功能。

## 运行环境与工具

- **仅使用规程与知识**：宿主能读取 `SKILL.md` 和按需引用的文件即可。
- **调用脚本**：Python 3.10+，六个运行脚本使用 Python 标准库，不需要单独的模型 API 密钥。
- **保存记录**：宿主需拥有用户授权目录的读写能力。

从技能目录执行以下命令：

```bash
cd skills/sales-dialogue-assistant

# 只读检索；分数是词汇相关度，不是成交概率
python scripts/knowledge.py search --query "合作 案例" --kind method --limit 3
python scripts/knowledge.py get --id M08

# 查看工作区工具的实际参数
python scripts/workspace.py --help

# 初始化指定的独立私人目录，然后读取实际记录
python scripts/workspace.py --workspace /your/private/sales-workspace init
python scripts/workspace.py --workspace /your/private/sales-workspace context
```

把 `/your/private/sales-workspace` 替换为自己系统中仓库之外的真实目录；Windows 可使用带引号的盘符路径。初始化不会覆盖已有记录，更新需要刚读到的版本号。其他命令见[工作区说明](skills/sales-dialogue-assistant/references/workspace-memory.md)。

六个脚本分别负责：

|脚本|实际职责|
|---|---|
|`knowledge.py`|编号读取、词汇与别名检索；不等于语义理解|
|`decision_engine.py`|确定性参考路由和条件检查；不代替模型判断|
|`diagnosis_report.py`|校验并生成结构化诊断报告|
|`case_learning.py`|案例记录、候选经验、审核后启停|
|`evaluation_tools.py`|处理已有对照答案和反馈；不自动生成模型答案或完成盲评|
|`workspace.py`|私人 Markdown 记录、版本控制、恢复、待办和产物结构检查|
|`setup_wechat.py` / `wechat_selftest.py`|隔离依赖安装、系统选择和真实CLI模拟自检|
|`wechat_context.py` / `wechat_runtime.py`|绑定账号、唯一好友匹配、指定私聊读取、ChatLab本地索引和检索|

脚本的结构检查无法识别所有自然语言矛盾、遗漏引用或改写后的内部信息，客户稿仍需逐项核对事实。

## 目录结构

```text
sales-dialogue-assistant/
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── docs/
│   └── VALIDATION.md
└── skills/
    └── sales-dialogue-assistant/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── references/          # 方法、证据与按需读取的工作规程
        ├── scripts/             # 原知识/记忆工具，以及微信CLI适配器
        ├── install.ps1 / install.sh
        ├── vendor/wechat-cli/   # 附带许可证及修改记录的源码
        └── assets/              # 模板、模拟示例、npm依赖锁文件
```

常用入口：[用户指南](skills/sales-dialogue-assistant/references/user-guide.md) · [自然使用示例](skills/sales-dialogue-assistant/references/usage-examples.md) · [中性判断](skills/sales-dialogue-assistant/references/neutral-assessment.md) · [综合工作台](skills/sales-dialogue-assistant/references/sales-workbench.md) · [嵌入说明](skills/sales-dialogue-assistant/references/embedding.md)。

## 知识与公开副本

技能包含 **43 张方法卡、71 条话术模板、1,063 条案例记录、5,711 条证据记录**。这些是方法学习材料，可能包含教学例、自报结果和未知结果，不能把数量理解为独立成功验证，也不能当作使用者自己的项目履历。

资料保留匿名来源编号、段落、时间及上下文；身份脱敏不意味着无法通过原句反向检索。本 GitHub 副本在 2.7.0 匿名包基础上额外移除了不必要的云端附件资源标识；未包含原始 PDF、媒体、私人记忆和客户档案。

## 版本与验证状态

- **2.8.0**：本机微信指定私聊读取、ChatLab本地检索、按系统安装及首次模拟自检。媒体内容未自动识别，不自动发消息。
- **2.7.0**：中性判断、具体自然表达、方法对行动的实际影响。
- **2.6.0**：双方记忆、业务资料、商机、产物版本及综合工作流。
- **2.5.0**：根据会话与条件选择方法，而不依赖场景穷举。

`pre-release` 是当前内测分支。没有发布 GitHub Release，也未宣称生产环境或真实成交效果已验证。

已完成的本地程序检查、此次公开副本检查和未执行项目，见[验证说明](docs/VALIDATION.md)。设计题的输出与评分为空时，表示尚未执行，不是测试通过。

## 常见问题

**装完为什么没自动使用？** 先新开会话，或明确要求使用 `sales-dialogue-assistant`；确认整个技能目录可读，不能只有入口文件。

**可以只报客户昵称吗？** 可以，例如“帮我看看微信里的张三，别替我乐观”。需要本机微信数据可读且账号已连接；重名会让你确认，不会默认第一个。

**聊天会放在哪？** 默认保存在用户主目录的 `.sales-dialogue-assistant/wechat/`，不进入Skill或Git。底层分片解密缓存可能包含其他会话，适配器仅返回选定私聊。用云模型分析时，选定内容会进入当前模型上下文，不能理解为全程离线。

**隔几天回来为什么不记得？** 确认上次确实保存成功，当前宿主使用同一个私人工作区；普通聊天附件不保证持久保存。

**会替我联系客户、发报价吗？** 默认只生成草稿，不自动发送，不代表用户批准商业承诺。

**可以保证识别客户真实意图或提高成交率吗？** 不可以。意图是基于现有材料的解释，需随反馈修正；效果需要真实使用和业务验证。

**能直接导入我的成功案例自动变聪明吗？** 可以按授权记录实际过程和结果；推广成经验须检查来源、适用条件与反例，不因一次成功自动改写通用规则。

## 反馈、隐私与许可

使用问题请参考[反馈指南](CONTRIBUTING.md)。不要在公开 Issue 中提交客户原始聊天、联系方式、合同、私人记忆或凭据；安全与隐私说明见[SECURITY.md](SECURITY.md)。

**目前未指定开源许可证。** 本仓库未附带统一的授权许可；资料中的第三方内容不因仓库公开而被重新授权。需要复用、再分发或商用时，请先明确相关授权范围。

新增第三方程序保留各自许可：随包WeChat CLI源码采用Apache-2.0；ChatLab CLI由npm独立安装、遵循其AGPL-3.0许可。具体来源、版本和修改见[第三方声明](skills/sales-dialogue-assistant/THIRD_PARTY_NOTICES.md)。本仓库的未授权声明不替代这些组件的原许可。
