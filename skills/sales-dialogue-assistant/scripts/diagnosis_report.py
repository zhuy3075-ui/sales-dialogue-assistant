"""Validate source/utterance references and render a model-authored diagnosis report."""
import argparse
import json
import re
from pathlib import Path
from knowledge import Knowledge

ROOT=Path(__file__).resolve().parents[1]


def require_text(value,name):
    if not isinstance(value,str) or not value.strip():raise ValueError(name+' must be nonempty text')


def validate(d,kb):
    if not isinstance(d,dict):raise ValueError('Diagnosis must be an object')
    for k in ('report_id','title','summary','goal','relationship','stage'):require_text(d.get(k),k)
    if type(d.get('simulation')) is not bool:raise ValueError('simulation must be explicit')
    utterances=d.get('utterances')
    if not isinstance(utterances,list) or not utterances:raise ValueError('Need transcript/statement records')
    u={}
    for x in utterances:
        if not isinstance(x,dict) or not re.fullmatch(r'U\d+',str(x.get('id',''))):raise ValueError('Invalid U id')
        if x['id'] in u:raise ValueError('Duplicate U id')
        for k in ('speaker','text'):require_text(x.get(k),k)
        u[x['id']]=x
    def refs(items):
        if not isinstance(items,list) or not items or any(x not in u for x in items):raise ValueError('Invalid/missing dialogue refs: '+str(items))
    def sources(items):
        if not isinstance(items,list) or not items:raise ValueError('Need knowledge sources')
        for identity in items:
            if not isinstance(identity,str) or not re.fullmatch(r'[MTEC]\d+',identity):raise ValueError('Invalid author knowledge ID '+str(identity))
            kb.get(identity)
    def records(key,prefix,required,allow_empty=False):
        rows=d.get(key)
        if not isinstance(rows,list) or (not rows and not allow_empty):raise ValueError(key+' must be an array; empty only when no finding')
        seen=set()
        for r in rows:
            if not isinstance(r,dict) or not re.fullmatch(prefix+r'\d+',str(r.get('id',''))) or r['id'] in seen:raise ValueError('Invalid/duplicate '+prefix+' id')
            seen.add(r['id'])
            for k in required:require_text(r.get(k),key+'.'+k)
        return seen
    intents=records('intents','I',('hypothesis','alternative','verification','counterevidence','response_implication'))
    for i in d['intents']:
        refs(i.get('dialogue_refs'))
        if i.get('kind') not in ('explicit','hypothesis'):raise ValueError('Invalid intent kind')
        if i.get('confidence') not in ('高','中','低'):raise ValueError('Invalid confidence')
        if i['kind']=='hypothesis' and i['confidence']=='高':raise ValueError('Unconfirmed motive hypothesis cannot be high confidence')
    risks=records('risks','R',('title','trigger','impact','mitigation','status','likelihood'),True)
    for r in d['risks']:
        refs(r.get('dialogue_refs'));sources(r.get('source_ids'))
        if r.get('severity') not in ('高','中','低'):raise ValueError('Invalid severity')
    records('issues','D',('original_quote','problem','cause_hypothesis','impact','rewritten','why','verification'),True)
    for issue in d['issues']:
        refs(issue.get('dialogue_refs'));sources(issue.get('source_ids'))
        if not any(issue['original_quote'] in u[x]['text'] for x in issue['dialogue_refs']):raise ValueError('Misquoted original: '+issue['id'])
        if not isinstance(issue.get('correction_steps'),list) or not issue['correction_steps']:raise ValueError('Missing correction steps')
        for t in issue['correction_steps']:require_text(t,'correction step')
        if not isinstance(issue.get('risk_ids'),list) or any(x not in risks for x in issue['risk_ids']):raise ValueError('Invalid issue risks')
    records('responses','A',('text','applicability','stop_condition','status'))
    for response in d['responses']:
        if not isinstance(response.get('sentence_analysis'),list) or not response['sentence_analysis']:raise ValueError('Need sentence analysis')
        if response['status'] not in ('可发送草稿','待填草稿'):raise ValueError('Invalid draft status')
        if response['status']=='可发送草稿' and re.search(r'【[^】]+】|\{[^}]+\}',response['text']):raise ValueError('Unfilled slots cannot be sendable')
        for s in response['sentence_analysis']:
            require_text(s.get('sentence'),'sentence');require_text(s.get('function'),'function');require_text(s.get('tone'),'tone')
            if s['sentence'] not in response['text']:raise ValueError('Analyzed sentence missing from response')
            if not isinstance(s.get('intent_ids'),list) or any(i not in intents for i in s['intent_ids']):raise ValueError('Invalid sentence intent references')
            if not isinstance(s.get('risk_ids'),list) or any(i not in risks for i in s['risk_ids']):raise ValueError('Invalid sentence risk references')
            sources(s.get('source_ids'))
        covered=[False]*len(response['text'])
        for s in response['sentence_analysis']:
            start=0
            while True:
                start=response['text'].find(s['sentence'],start)
                if start<0:break
                covered[start:start+len(s['sentence'])]=[True]*len(s['sentence'])
                start+=len(s['sentence'])
        if any(not ok and char.strip() for ok,char in zip(covered,response['text'])):
            raise ValueError('Response contains text without sentence analysis: '+response['id'])
    for k in ('known_facts','unknowns','next_steps','success_checks'):
        if not isinstance(d.get(k),list):raise ValueError(k+' must be array')
        for x in d[k]:require_text(x,k)
    return {'utterances':len(u),'intents':len(intents),'risks':len(risks),'issues':len(d['issues']),'responses':len(d['responses']),
            'scope':'结构、原句一致性、引用编号检查；没有自动验证意图、语义判断或业务效果'}


def render(d,kb):
    checks=validate(d,kb)
    lines=['# '+d['title'],'',f"报告：{d['report_id']}｜Skill 2.1.0｜"+('**模拟案例，未发生真实交易**' if d['simulation'] else '**依据用户所给材料，核验范围见正文**'),'',
        '## 1. 结论摘要','',d['summary'],'','## 2. 事实、现场与缺口','',f"目标：{d['goal']}。关系：{d['relationship']}。阶段：{d['stage']}。",'']
    for f in d['known_facts']:lines+=['- 已知：'+f]
    for f in d['unknowns']:lines+=['- 待核：'+f]
    for u in d['utterances']:lines+=['',f"**{u['id']}｜{u['speaker']}｜{u.get('time') or '时间未提供'}**",'', '> '+u['text'].replace('\n','\n> ')]
    lines+=['','## 3. 甲方意图分析','']
    for i in d['intents']:
        lines += [f"### {i['id']}｜{i['hypothesis']}",'',f"性质：{'明确表达' if i['kind']=='explicit' else '分析者假设'}；置信度：{i['confidence']}；对话依据：{', '.join(i['dialogue_refs'])}。",'',
            '替代解释：'+i['alternative'],'','反向证据/缺口：'+i['counterevidence'],'','验证：'+i['verification'],'','回应含义：'+i['response_implication'],'']
    lines+=['## 4. 风险点分析','']
    if not d['risks']:lines+=['在所给材料范围内未发现可核定风险；不代表未来没有风险。','']
    for r in d['risks']:
        lines += [f"### {r['id']}｜{r['title']}",'',f"严重度：{r['severity']}；状态：{r['status']}；发生可能性：{r['likelihood']}。",'',
            '触发：'+r['trigger'],'','影响：'+r['impact'],'','处置：'+r['mitigation'],'',f"对话：{', '.join(r['dialogue_refs'])}；知识：{', '.join(r['source_ids'])}。",'']
    lines+=['## 5. 谈单话术诊断与纠正','']
    if not d['issues']:lines+=['在所给材料范围内未发现需要纠正的问题；不为填满报告虚构错误。','']
    for x in d['issues']:
        lines += [f"### {x['id']}｜{x['problem']}",'',f"原句（{', '.join(x['dialogue_refs'])}）：",'','> '+x['original_quote'],'',
            '原因假设：'+x['cause_hypothesis'],'','可能影响：'+x['impact'],'','纠正方法：','']
        lines += [f'{i}. {t}' for i,t in enumerate(x['correction_steps'],1)]
        lines += ['','替代说法（分析者新拟，核实事实后使用）：','','> '+x['rewritten'],'','修改理由：'+x['why'],'','检验：'+x['verification'],'',
            f"对应风险：{', '.join(x['risk_ids'])}；知识依据：{', '.join(x['source_ids'])}。",'']
    lines+=['## 6. 回应候选及逐句话术分析','']
    for x in d['responses']:
        lines += [f"### {x['id']}｜{x['status']}",'','适用：'+x['applicability'],'','**以下为分析者新拟，不是作者原句。**','','> '+x['text'].replace('\n','\n> '),'']
        for s in x['sentence_analysis']:
            lines += ['- **'+s['sentence']+'**：'+s['function']+'；语气：'+s['tone']+f"；对应{', '.join(s['intent_ids']+s['risk_ids'])}；方法/来源：{', '.join(s['source_ids'])}。"]
        lines+=['','停止/退出条件：'+x['stop_condition'],'']
    lines+=['## 7. 下一步与复盘','']
    lines += ['- 动作：'+s for s in d['next_steps']]+['- 检验：'+s for s in d['success_checks']]
    ids=set()
    for r in d['risks']+d['issues']:ids.update(r['source_ids'])
    for r in d['responses']:
        for s in r['sentence_analysis']:ids.update(s['source_ids'])
    lines+=['','## 知识出处索引','', 'U编号只表示本次对话；M/T/C/E表示原知识库。两者不能互相冒充。用knowledge.py get --id读取完整记录与上下文。','']
    for identity in sorted(ids):
        r=kb.get(identity)
        if r['kind']=='evidence':
            lines += [f"- {identity}：《{r['title']}》｜{r.get('heading') or '章节未知'}｜{r.get('date') or '日期未知'}（{r.get('date_basis','')}）｜{r['speaker']}｜{r['pid']}｜行{r['line_start']}—{r['line_end']}。原句：{r['quote']}"]
        elif r['kind']=='method':lines += [f"- {identity}：{r['title']}；代表来源：{', '.join(r['representative_evidence'])}；操作化可信度：{r['operational_confidence']}。"]
        else:lines += [f"- {identity}：{r.get('title') or r.get('scene')}；类型：{r['kind']}。"]
    lines+=['','校验范围：'+checks['scope']+'。正式效果仍需实际执行与业务验证。','']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path)
    a=p.parse_args();d=json.loads(a.input.read_text('utf-8-sig'));content=render(d,Knowledge())
    if not a.output:print(content);return
    target=a.output.resolve()
    if ROOT==target or ROOT in target.parents or any(part.startswith('L1-') for part in target.parts):raise ValueError('Report must be outside Skill and L1')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as f:f.write(content)
    print(json.dumps({'report':str(target),'simulation':d['simulation'],'semantic_review':'由撰写代理负责；工具仅校验引用与格式'},ensure_ascii=False))


if __name__=='__main__':main()
