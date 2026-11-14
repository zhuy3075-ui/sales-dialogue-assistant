# 用户案例学习与局部进化

版本2.1.0。触发：用户分享成功/失败、给出实际反馈并希望记住或优化。当前会话里的普通引用不自动收录为长期经验；授权范围只在本地用户案例库，不外部上传。

## 从分享走到可调用经验

1. **原样留存**。保存用户讲述raw_text，按U编号保留对话；补业务、阶段、目标、实际发送、客户反应和付款/退款/交付状态。缺失写unknown，不把“成功了”展开成全款到账与交付满意。原稿不可覆盖，补充用新UC编号和supersedes关联旧稿。
2. **还原因果限制**。区分作者方法、自己的改法、实际采用的说法与同时变化的其他因素。确认一次机会、同一客户、相同结果是否被重复登记。相同案例跨日的补充不算独立验证。
3. **匹配旧知识**。查相关M/T/C/E；如果只是既有方法的新例子，挂新案例，不再造一个同义方法。与原方法冲突时并列条件和结果，先作为反例待核。
4. **提出局部候选LR**。只选三类低影响变化：example（有限条件下的例句/做法）、clarification（必要澄清问题）、narrower_condition（收窄原方法适用条件）。写清业务、阶段、成立条件、来源UC、基于哪些M、为何需要、何时禁用。core_rule可保存为提案，但不能由自动激活通道改写核心Skill。
5. **审查与测试**。回查UC原话与实际结果，查有无虚构承诺、违背旧权益/拒绝联系、扩张到别的业务。至少一次范围内样例和一次边界反例，保存输入、预期、观察结果、是否通过。若缺证据、测试失败或存在未解决冲突，保持候选。
6. **限定激活**。语义审查通过后，由智能体生成独立review记录绑定LR内容SHA；本地工具校验记录和状态，才写active事件。若用户只提供模拟案例、未授权学习、核心规则修改或缺反例，拒绝激活。工具不会判断语义审查是否诚实，代理必须实际读证据、做测试，不能为了过门槛编造pass。
7. **调用和修正**。下次匹配业务、阶段与条件时作为用户局部经验参考，与作者方法并列标出处。报告负面结果或用户要求撤销时deactivate，默认检索不再选它，历史不删除；新版候选用新LR编号关联旧版。

没有后台监听、无人值守训练或自动部署；每次学习在用户发起的会话内执行。局部经验不改变基础Skill的全局优先级。业务渠道发布及新的高风险行动按实际授权执行。

## 输入合同

UC字段：`case_id`（UC-前缀）、`scenario`、`raw_text`、`context.business/stage`、`utterances`、`result`、`other_factors`、`use_for_learning`、`simulation`。可有`supersedes`。result必须含status（unknown/pending/reported/verified）、payment_stage（unknown/none/intent/deposit/full）、refund_status（unknown/none_reported/requested/refunded）、delivery_status（unknown/not_started/in_progress/completed_reported/completed_verified）、evidence_refs。verified还要核验说明及实际证据，不自动由工具核实流水。

LR字段：`proposal_id`（LR-前缀）、`kind`、`case_ids`、`base_methods`、`scope.business/stage/conditions`、`content`、`rationale`、`counterexamples`。scope不得写全部业务；必须与支持案例的业务/阶段一致。单案例不能保证普遍有效。scope中的其他条件仍需调用时逐项核实。

review字段：`proposal_sha256`、`reviewer`、`reason`、`provenance_check/scope_check/conflict_check`、`checks`。三项核验须为pass，checks同时包含in_scope及boundary，每项有input/expected/observed/passed。评审可由当前智能体执行并如实标身份；这不叫独立盲评。核心规则修改另走[版本协议](evaluation-evolution.md)。

## 命令与保存

所有用户记录存Skill以外的目录，例如项目`蒸馏成果/用户案例库`；不把私人案例默认装入通用Skill ZIP。

```text
python scripts/case_learning.py --store /项目/用户案例库 ingest --input /临时/案例.json
python scripts/case_learning.py --store /项目/用户案例库 propose --input /临时/候选.json
python scripts/case_learning.py --store /项目/用户案例库 activate --id LR-001 --review /临时/审查.json
python scripts/case_learning.py --store /项目/用户案例库 deactivate --id LR-001 --reason "用户要求停用或发现边界反例"
```

ingest原稿、propose候选、activate/deactivate事件均独立保存；不覆盖文件。相同ID和相同原稿可识别重复，内容变化需要新修订。多次修订共用root_case_id，不算独立案例。知识检索可按编号审查所有历史，默认主题检索排除未授权学习及已被修订的旧个案，不注入候选/停用经验。支持案例出现新修订时，旧active经验读取为needs_review，默认停止调用；依据最新案例重新提出并审查LR，不能直接重激活旧来源版本。

## 判定口径

可激活的是“在这些前提下增加这句澄清/采用这段表达”的局部建议，不是“已经证明能增加成交率”。既有作者M仍保留原置信度；UC标用户自报；LR标局部操作假设。有效性提升要等多次包含失败的真实记录及可比分析，不设一个虚假的固定成功次数门槛。

如新经验与客户明确要求、旧约或产品事实冲突，先停用经验；若只是不同关系或阶段，改写更窄条件后重测。原始成功和负面结果都保留，不只保存有利证据。


> 外发版本说明：本文件已作身份脱敏，引用为脱敏转录。历史原件校验不等于当前副本逐字未变；完整原件、私有路径和外部身份链接不随包。


### 嵌入宿主的保存边界

只有实际写入成功才报告已保存，实际激活成功才报告已启用。无持久化工具或权限时只整理待保存内容，明确尚未长期保存；不能沿用开发会话授权假设所有宿主都有写权限。默认简短回执，详细来源与步骤按需展开。

## 策略反馈追踪（2.2.0）

销售案例按[反馈规程](sales-feedback.md)同时记录所选方案、实际发送、客户反应及结果。仅有成功自报不提高基础方法可信度；只在既有LR检查通过后增加限定经验。
