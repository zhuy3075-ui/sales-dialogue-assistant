"""Append-only user cases and scoped learning overlays; never rewrite author knowledge."""
import argparse
import hashlib
import json
import re
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def read(p):return json.loads(Path(p).read_text('utf-8-sig'))


def sha(obj):return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()


def identifier(value,prefix):
    if not isinstance(value,str) or not re.fullmatch(prefix+r'-[A-Za-z0-9][A-Za-z0-9_-]{0,79}',value):
        raise ValueError(f'Invalid {prefix} id: {value!r}')
    return value


def text(value,name):
    if not isinstance(value,str) or not value.strip():raise ValueError(name+' must be nonempty text')


def strings(value,name,required=True):
    if not isinstance(value,list) or (required and not value) or any(not isinstance(x,str) or not x.strip() for x in value):raise ValueError(name+' must be a text array')


def store_path(path):
    p=Path(path).resolve()
    if p==ROOT or ROOT in p.parents or any(part.startswith('L1-') for part in p.parts):
        raise ValueError('User learning store must be outside Skill and frozen L1')
    return p


def save_new(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')


def ingest(store,payload):
    store=store_path(store);c=dict(payload);identifier(c.get('case_id'),'UC')
    for k in ('scenario','raw_text'):text(c.get(k),k)
    if type(c.get('simulation')) is not bool:raise ValueError('simulation must be boolean')
    if type(c.get('use_for_learning')) is not bool:raise ValueError('use_for_learning must be boolean')
    if not isinstance(c.get('context'),dict):raise ValueError('context must be object')
    for k in ('business','stage'):text(c['context'].get(k),'context.'+k)
    result=c.get('result')
    if not isinstance(result,dict) or result.get('status') not in ('unknown','pending','reported','verified'):raise ValueError('Invalid result status')
    for k,values in {'payment_stage':['unknown','none','intent','deposit','full'],
                     'refund_status':['unknown','none_reported','requested','refunded'],
                     'delivery_status':['unknown','not_started','in_progress','completed_reported','completed_verified']}.items():
        if result.get(k) not in values:raise ValueError('Invalid result.'+k)
    strings(result.get('evidence_refs',[]),'result.evidence_refs',False)
    if result['status']=='verified':
        if c['simulation'] or not result.get('evidence_refs') or not result.get('verification_note'):
            raise ValueError('Verified real result requires evidence, verification note and non-simulation')
    u=c.get('utterances',[])
    if not isinstance(u,list):raise ValueError('utterances must be list')
    seen=set()
    for line in u:
        if not isinstance(line,dict) or not re.fullmatch(r'U\d+',str(line.get('id',''))):raise ValueError('Invalid utterance id')
        if line['id'] in seen:raise ValueError('Duplicate utterance '+line['id'])
        seen.add(line['id']);text(line.get('text'),'utterance text');text(line.get('speaker'),'speaker')
        if line['text'] not in c['raw_text']:raise ValueError('Utterance not preserved in raw_text: '+line['id'])
    strings(c.get('other_factors',[]),'other_factors',False)
    target=store/'cases'/(c['case_id']+'.json')
    if target.exists():
        old=read(target)
        if old['input_sha256']==sha(payload):return {'case_id':c['case_id'],'status':'already_recorded','path':str(target)}
        raise FileExistsError('Case id exists with different content; create a new revision id with supersedes, never overwrite')
    rawhash=hashlib.sha256(c['raw_text'].encode('utf-8')).hexdigest()
    previous=None
    if c.get('supersedes'):
        identifier(c['supersedes'],'UC')
        previous_path=store/'cases'/(c['supersedes']+'.json')
        if not previous_path.exists():raise ValueError('Unknown superseded case')
        previous=read(previous_path)
    root_id=previous.get('root_case_id',previous['case_id']) if previous else c['case_id']
    for p in (store/'cases').glob('UC-*.json'):
        old=read(p)
        if old['raw_sha256']==rawhash and old.get('root_case_id',old['case_id'])!=root_id:
            raise ValueError('Duplicate raw case already recorded as '+old['case_id'])
    c.update({'provenance_namespace':'user_case','input_sha256':sha(payload),'raw_sha256':rawhash,
              'root_case_id':root_id,'created_ns':time.time_ns(),
              'interpretation':'用户提供的个案；核验状态按实际记录，成功序列不能证明话术因果，不归属资料作者'})
    save_new(target,c)
    return {'case_id':c['case_id'],'status':'recorded','path':str(target),'eligible_for_learning':c['use_for_learning']}


def propose(store,payload):
    store=store_path(store);p=dict(payload);identifier(p.get('proposal_id'),'LR')
    if p.get('kind') not in ('example','clarification','narrower_condition','core_rule'):raise ValueError('Invalid proposal kind')
    for key in ('content','rationale'):text(p.get(key),key)
    strings(p.get('case_ids'),'case_ids');strings(p.get('base_methods'),'base_methods')
    scope=p.get('scope')
    if not isinstance(scope,dict):raise ValueError('scope must be object')
    for key in ('business','stage'):text(scope.get(key),'scope.'+key)
    strings(scope.get('conditions'),'scope.conditions')
    if scope['business'] in ('all','*','所有','全部') or scope['stage'] in ('all','*','所有','全部'):raise ValueError('No global scope for local learning')
    base={m['id'] for m in read(ROOT/'references/method-cards.json')['methods']}
    if set(p['base_methods'])-base:raise ValueError('Unknown base method')
    strings(p.get('counterexamples',[]),'counterexamples',False)
    simulation=False
    for cid in p['case_ids']:
        identifier(cid,'UC');c=read(store/'cases'/(cid+'.json'))
        if not c['use_for_learning']:raise ValueError('Case is not authorized for learning: '+cid)
        if c['context']['business']!=scope['business'] or c['context']['stage']!=scope['stage']:raise ValueError('Scope expands beyond supporting case '+cid)
        simulation=simulation or c['simulation']
    p.update({'provenance_namespace':'user_learning','simulation':simulation,'input_sha256':sha(payload),
              'limits':'单案例只支持限定情境候选；收益与普遍有效性未知；不得覆盖原始作者层或核心边界'})
    target=store/'proposals'/(p['proposal_id']+'.json');save_new(target,p)
    return {'proposal_id':p['proposal_id'],'state':'candidate','path':str(target),'simulation':simulation}


def transition(store,proposal_id,state,review=None,reason=None):
    store=store_path(store);identifier(proposal_id,'LR')
    p=read(store/'proposals'/(proposal_id+'.json'))
    if state not in ('active','inactive'):raise ValueError('Unsupported state')
    if state=='active':
        if p['kind']=='core_rule':raise ValueError('Core rule edits require a separate explicit version change; overlay activation cannot rewrite core')
        if p['simulation']:raise ValueError('Simulated cases cannot activate real user learning')
        if not p['counterexamples']:raise ValueError('Need at least one counterexample/boundary')
        if not isinstance(review,dict):raise ValueError('Separate review record required')
        if review.get('proposal_sha256')!=sha(p):raise ValueError('Review must bind the exact proposal hash')
        for key in ('reviewer','reason'):text(review.get(key),key)
        for key in ('provenance_check','scope_check','conflict_check'):
            if review.get(key)!='pass':raise ValueError('Unpassed review gate: '+key)
        checks=review.get('checks',[])
        if not isinstance(checks,list) or len(checks)<2 or {x.get('kind') for x in checks}!={'in_scope','boundary'}:
            raise ValueError('Require in_scope and boundary tests')
        for check in checks:
            for key in ('input','expected','observed'):text(check.get(key),'check.'+key)
            if check.get('passed') is not True:raise ValueError('A review test has not passed')
        for cid in p['case_ids']:
            if not read(store/'cases'/(cid+'.json'))['use_for_learning']:raise ValueError('Learning permission missing')
            if any(read(f).get('supersedes')==cid for f in (store/'cases').glob('UC-*.json')):
                raise ValueError('Supporting case has a new revision; create a new proposal from the latest case')
        explanation='限定场景局部经验已激活；工具只核记录完整性，语义审查由记录中的reviewer负责，不代表因果有效性验证'
    else:
        text(reason,'reason');explanation='已停用，历史保留；默认检索不再注入该经验'
    event={'proposal_id':proposal_id,'state':state,'proposal_sha256':sha(p),'review':review if state=='active' else None,
           'reason':reason,'timestamp_ns':time.time_ns(),'meaning':explanation}
    target=store/'events'/f"{proposal_id}--{event['timestamp_ns']}.json";save_new(target,event)
    return {'proposal_id':proposal_id,'state':state,'event':str(target),'meaning':explanation}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--store',required=True,type=Path)
    sub=ap.add_subparsers(dest='command',required=True)
    for name in ('ingest','propose'):
        p=sub.add_parser(name);p.add_argument('--input',required=True,type=Path)
    p=sub.add_parser('activate');p.add_argument('--id',required=True);p.add_argument('--review',required=True,type=Path)
    p=sub.add_parser('deactivate');p.add_argument('--id',required=True);p.add_argument('--reason',required=True)
    a=ap.parse_args()
    if a.command=='ingest':result=ingest(a.store,read(a.input))
    elif a.command=='propose':result=propose(a.store,read(a.input))
    elif a.command=='activate':result=transition(a.store,a.id,'active',read(a.review))
    else:result=transition(a.store,a.id,'inactive',reason=a.reason)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
