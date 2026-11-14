"""Offline blind packaging and feedback validation; never generate business results."""
import argparse
import hashlib
import json
import random
import re
import secrets
from pathlib import Path


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def write_new(path, obj):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation preserves first-generation evaluation artifacts.
    with path.open('x',encoding='utf-8') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)
        f.write('\n')


def blind(records, seed=None):
    if not isinstance(records,list) or not records:raise ValueError('Expected nonempty paired-record array')
    if any(not isinstance(r,dict) for r in records):raise ValueError('Each record must be an object')
    ids=[r.get('id') for r in records]
    if any(not isinstance(i,str) or not i.strip() for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Each pair needs a unique nonempty text id')
    seed=secrets.randbits(128) if seed is None else seed
    rng=random.Random(seed)
    ordered=list(records);rng.shuffle(ordered)
    packet=[];mapping=[];leaks=[]
    for i,r in enumerate(ordered,1):
        for key in ('prompt','ordinary','skill'):
            if not isinstance(r.get(key),str) or not r[key].strip():raise ValueError(f'{r["id"]}: missing {key}')
        labels=['ordinary','skill'];rng.shuffle(labels)
        blind_id=f'B{i:03d}'
        packet.append({'id':blind_id,'prompt':r['prompt'],'known_facts':r.get('known_facts',[]),'X':r[labels[0]],'Y':r[labels[1]]})
        mapping.append({'id':blind_id,'source_id':r['id'],'X':labels[0],'Y':labels[1],
                        'ordinary_sha256':digest(r['ordinary']),'skill_sha256':digest(r['skill'])})
        for key in ('ordinary','skill'):
            if re.search(r'\bskill\b|M\d{2}\b|本技能|加载方法库',r[key],re.I):
                leaks.append({'source_id':r['id'],'side':key,'reason':'答案可能自曝方法来源；不自动删改，协调者需记录泄盲风险'})
    return ({'kind':'anonymous_text_evaluation','business_results':False,'cases':packet},
            {'seed':seed,'mapping':mapping,'leak_warnings':leaks,'rule':'仅协调者保管；评分冻结前不交评审'})


def feedback(record):
    required=('record_id','version','date','problem_type','context','selected_plan','adoption','actual_reply',
              'human_edits','reason','outcome','evidence_refs','allow_revision_use','simulation')
    missing=[k for k in required if k not in record]
    if missing:raise ValueError(f'Missing feedback fields: {missing}')
    for k in ('record_id','version','date','problem_type','context','selected_plan','actual_reply','human_edits','reason'):
        if not isinstance(record[k],str):raise ValueError(f'{k} must be text')
    if not record['record_id'].strip():raise ValueError('record_id cannot be blank')
    if record['adoption'] not in ('not_used','draft_only','sent','unknown'):raise ValueError('Invalid adoption')
    if type(record['allow_revision_use']) is not bool or type(record['simulation']) is not bool:raise ValueError('Consent and simulation must be boolean')
    if not isinstance(record['evidence_refs'],list) or any(not isinstance(x,str) for x in record['evidence_refs']):raise ValueError('evidence_refs must be text array')
    outcome=record['outcome']
    if not isinstance(outcome,dict) or outcome.get('status') not in ('unknown','pending','reported','verified'):raise ValueError('Invalid outcome status')
    if outcome['status']=='verified' and (not record['evidence_refs'] or record['simulation']):
        raise ValueError('Verified real outcomes need evidence and cannot be simulation')
    if record['adoption']=='sent' and not record['actual_reply'].strip():raise ValueError('Sent reply cannot be empty')
    return {'valid_structure':True,'simulation':record['simulation'],
            'business_effectiveness':'未由格式校验验证；需按协议核查真实证据',
            'eligible_for_revision_review':record['allow_revision_use']}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    subs=ap.add_subparsers(dest='command',required=True)
    p=subs.add_parser('blind');p.add_argument('--input',required=True,type=Path);p.add_argument('--output-dir',required=True,type=Path)
    p=subs.add_parser('feedback');p.add_argument('--input',required=True,type=Path)
    args=ap.parse_args()
    if args.command=='feedback':print(json.dumps(feedback(read(args.input)),ensure_ascii=False,indent=2));return
    if args.output_dir.exists():raise FileExistsError('Use a new output directory to preserve first answers and mappings')
    root=Path(__file__).resolve().parents[1]
    target=args.output_dir.resolve()
    if root.resolve()==target or root.resolve() in target.parents or 'L1-原始层封存-P2.71' in target.parts:
        raise ValueError('Evaluation output must be outside Skill and frozen L1')
    packet,mapping=blind(read(args.input))
    # Prepare both in memory before any mutation; no partial invalid input output.
    write_new(target/'review/anonymous-packet.json',packet)
    write_new(target/'private/reveal.json',mapping)
    score_template=[{'id':r['id'],'reviewer':'','X':{'scores':{'judgment':None,'response':None,'evidence':None,'boundary':None,'style':None},'hard_failures':[]},'Y':{'scores':{'judgment':None,'response':None,'evidence':None,'boundary':None,'style':None},'hard_failures':[]},'preference':'pending','reason':''} for r in packet['cases']]
    write_new(target/'review/scores-template.json',score_template)
    print(json.dumps({'cases':len(packet['cases']),'status':'待独立评审；尚无得分','leak_warnings':len(mapping['leak_warnings'])},ensure_ascii=False))


if __name__=='__main__':main()
