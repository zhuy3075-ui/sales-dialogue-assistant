"""Local, deterministic methodology planner. No network, customer messaging or L1 writes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

VERSION = '2.0.0'
ROOT = Path(__file__).resolve().parents[1]
ALLOWED_FACTS = {
    'paid_obligation': (True, False, None),
    'complaint_open': (True, False, None),
    'refund_requested': (True, False, None),
    'direct_price_request': (True, False, None),
    'price_known': (True, False, None),
    'scope_known': (True, False, None),
    'existing_terms_known': (True, False, None),
    'has_new_value': (True, False, None),
    'can_change_scope': (True, False, None),
    'decision_authority': (True, False, None),
    'wants_listening_only': (True, False, None),
    'borrowing_to_buy': (True, False, None),
    'contact_preference': ('allowed', 'stop_marketing', 'customer_will_contact', 'unknown'),
    'delivery_capability': ('confirmed', 'insufficient', 'unknown'),
    'budget_fit': ('confirmed', 'insufficient', 'unknown'),
}

# A = respond to the current task within the present scope.
# B = reduce commitment / validate first; B is not a harder sell.
ROUTES = {
 '求助初接触': {'keywords':['求助','初次','请教','打招呼'], 'a':['M09','M27','M08'], 'b':['M27','M12'], 'difference':'A把来意与一个请求说完整；B先自行补材料和试做，再带具体阻塞请教。'},
 '情绪回应': {'keywords':['情绪','生气','难过','委屈'], 'a':['M06','M05'], 'b':['M05','M30'], 'difference':'A先倾听承接；B在对方愿意解决时把情绪与实际问题拆开。'},
 '免费索取': {'keywords':['白嫖','免费','追问','范围外'], 'a':['M10','M09'], 'b':['M10','M36'], 'difference':'A说明范围并提供已有答复；B仅在有真实供给且对方愿意时讨论新服务，或结束新增请求。'},
 '合作洽谈': {'keywords':['合作','分佣','合伙','结算'], 'a':['M11','M39'], 'b':['M40','M11'], 'difference':'A明确分工后按完整范围合作；B用投入受限的小试点验证互补性。'},
 '需求澄清': {'keywords':['需求','怎么做','怎么办','流程','适合'], 'a':['M08','M35'], 'b':['M01','M04'], 'difference':'A回答已知并补一个关键信息；B先核适配和事实，必要时暂停推荐。'},
 '报价嫌贵': {'keywords':['报价','价格','多少钱','太贵','嫌贵'], 'a':['M17','M35'], 'b':['M17','M04'], 'difference':'A解释现有范围的真实报价；B仅在确有可选范围时比较减项，否则暂缓购买。'},
 '犹豫拖延': {'keywords':['犹豫','考虑','拖延','不买','暂缓'], 'a':['M19','M24'], 'b':['M24','M37'], 'difference':'A回应已提出的具体顾虑；B保留考虑空间，条件不足或拒绝时停止推进。'},
 '效果保证': {'keywords':['保证','回本','稳赚','效果'], 'a':['M18','M36'], 'b':['M04','M18'], 'difference':'A说清可控交付和不确定性；B若保证要求与真实能力不匹配则不接该交易。'},
 '投诉冲突': {'keywords':['投诉','退款','争议','冲突','不满意'], 'a':['M01','M30','M18'], 'b':['M10','M11'], 'difference':'A核事实并履行原有补救；B对争议范围书面核实或交有权限者处理，不借续费解决旧义务。'},
 '催进度': {'keywords':['催进度','延期','交付','进度','爽约'], 'a':['M39','M09'], 'b':['M13','M39'], 'difference':'A按真实依赖重排时间；B先完成最小可验收部分，再核剩余阻塞。'},
 '结束合作': {'keywords':['结束合作','停止','不联系','拉黑','退出'], 'a':['M10','M11'], 'b':['M11','M39'], 'difference':'A确认结束并结清原有责任；B存在交接义务时安排最小交接，不挽留推销。'},
 '复购转介绍': {'keywords':['续费','复购','转介绍','推荐朋友'], 'a':['M21','M13'], 'b':['M22','M21'], 'difference':'A先核交付及下一阶段需求；B在对方愿意且适合时提供低负担转介绍入口，不自动索取联系人。'},
 '内容引流': {'keywords':['引流','流量','内容','人设','账号','涨粉'], 'a':['M15','M42','M23'], 'b':['M38','M41','M40'], 'difference':'A修正内容到产品的承接；B先复用小批素材并核成本，验证后再扩大。'},
 '经营决策': {'keywords':['指标','利润','ROI','成本','复盘','决策','试点'], 'a':['M02','M41','M33'], 'b':['M26','M40'], 'difference':'A用完整成本和目标选择现有路径；B限定试点检验假设，再决定是否扩大。'},
}

FACT_QUESTIONS = {
 'paid_obligation':'这次请求是否属于已经购买或明确承诺的服务？',
 'existing_terms_known':'已有服务、退款、交付或结算约定是什么？',
 'contact_preference':'对方是否允许继续主动联系，还是要求自己再联系/停止营销？',
 'price_known':'当前真实价格或计价依据是什么？',
 'scope_known':'这项价格对应哪些已确认的交付与不包含项？',
 'delivery_capability':'当前已经具备什么可核实的交付能力和容量？',
 'budget_fit':'当前方案是否在客户可支配预算内？',
 'has_new_value':'这次回访有什么能回答上次问题的新信息？',
    'decision_authority':'谁有权批准本次合作、结算或范围变更？当前只能提交草案，不能代其承诺。',
}


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError('Input must be a JSON object')
    allowed={'problem','goal','types','facts','relationship','stage','known_facts','unknowns','constraints'}
    if set(payload)-allowed:
        raise ValueError(f'Unknown input fields: {sorted(set(payload)-allowed)}')
    if not isinstance(payload.get('problem'),str) or not payload['problem'].strip():
        raise ValueError('problem must be nonempty text')
    for key in ('goal','relationship','stage'):
        if key in payload and not isinstance(payload[key],str):
            raise ValueError(f'{key} must be text')
    types=payload.get('types',[])
    if not isinstance(types,list) or any(not isinstance(t,str) or t not in ROUTES for t in types):
        raise ValueError(f'types must be a list from {list(ROUTES)}; received {types!r}')
    if len(types)!=len(set(types)):
        raise ValueError('types must not contain duplicates')
    facts=payload.get('facts',{})
    if not isinstance(facts,dict) or set(facts)-set(ALLOWED_FACTS):
        raise ValueError(f'Invalid fact keys: {facts!r}')
    for k,v in facts.items():
        if not any(type(v) is type(a) and v==a for a in ALLOWED_FACTS[k]):
            raise ValueError(f'Invalid fact {k}={v!r}; allowed {ALLOWED_FACTS[k]}')
    for key in ('known_facts','unknowns','constraints'):
        if key in payload and (not isinstance(payload[key],list) or any(not isinstance(v,str) for v in payload[key])):
            raise ValueError(f'{key} must be a list of text')
    return payload


def plan(payload):
    validate(payload)
    library=json.loads((ROOT/'references/method-cards.json').read_text('utf-8'))
    cards={m['id']:m for m in library['methods']}
    facts=payload.get('facts',{})
    text=payload['problem']
    explicit=bool(payload.get('types'))
    detections=[{'type':t,'basis':'用户/调用者显式选择','score':None} for t in payload.get('types',[])]
    if not explicit:
        for t,r in ROUTES.items():
            hits=[w for w in r['keywords'] if w.lower() in text.lower()]
            if hits: detections.append({'type':t,'basis':'待确认关键词：'+','.join(hits),'score':len(hits)})
        detections.sort(key=lambda d:(-d['score'],list(ROUTES).index(d['type'])))
    types=[d['type'] for d in detections]
    # Explicit business facts override an omitted routing tag, never get dropped by a top-k cutoff.
    for condition,t in [(facts.get('complaint_open') is True or facts.get('refund_requested') is True,'投诉冲突'),
                        (facts.get('direct_price_request') is True,'报价嫌贵')]:
        if condition and t not in types:
            types.append(t);detections.append({'type':t,'basis':'已核结构化事实触发','score':None})
    result={'engine_version':VERSION,'input':payload,'classification':detections,
            'classification_status':'调用者已提供分类/事实，仍需核上下文' if explicit else '关键词候选；需要Skill语义确认，分值不是效果概率',
            'status':'ready_for_review','hard_constraints':[], 'questions':[], 'candidates':[],
            'conflict_resolutions':[], 'excluded':[],
            'limits':['只生成决策草稿，不发送、不签约、不收款','语义否定、隐喻、未知约束由调用者复核','所有业务有效性未验证']}
    def hard(code, explanation, refs):
        result['hard_constraints'].append({'id':code,'text':explanation,'method_ids':refs,'nature':'助理应用约束'})
    def need(key):
        missing = facts.get(key) in (None,'unknown') or (key in ('price_known','scope_known','existing_terms_known') and facts.get(key) is False)
        if missing and key not in [q['field'] for q in result['questions']]:
            result['questions'].append({'field':key,'question':FACT_QUESTIONS[key]})
    if not types:
        result['status']='insufficient_context'
        result['questions']=[{'field':'types','question':'当前最需要解决的是哪类问题，以及希望得到什么结果？'}]
        return result
    if not explicit:
        result['status']='conditional'
        result['questions'].append({'field':'types','question':'请确认上述候选类型是否符合上下文；尤其核对否定表达和引用内容。'})

    stop=facts.get('contact_preference') in ('stop_marketing','customer_will_contact')
    duty=facts.get('paid_obligation') is True or facts.get('complaint_open') is True or facts.get('refund_requested') is True
    listening=facts.get('wants_listening_only') is True
    insufficient=facts.get('delivery_capability')=='insufficient' or facts.get('budget_fit')=='insufficient' or facts.get('borrowing_to_buy') is True
    if stop:
        hard('H01','停止主动营销；按已核约定保留必要售后/退款处理。对方自行联系不等于授权定时催。',['M10','M20','M24'])
    if duty:
        hard('H02','先履行已有权益与争议处理，不以新付款、续费、好评、转介绍作为前置。',['M10','M13','M18'])
        if not listening:need('existing_terms_known')
    if insufficient:
        hard('H03','暂停当前购买推进；资金不足/借贷购买或交付能力不足时，不用话术掩盖。可提供信息或核实适合范围。',['M04','M18','M36'])
    if facts.get('direct_price_request') is True:
        hard('H04','先回答已知真实价格与范围；未知时说明计价依据或待核，不先拖入塑品。',['M17','M35'])
        need('price_known');need('scope_known')
    hard('H05','不得编造价格、期限、权限、经历、效果保证；候选只是待用户审阅的草稿。',['M01','M18','M36'])
    if facts.get('decision_authority') is False:
        hard('H07','当前没有决策权限；合作、结算、排期或范围变化只作待审批草案，不代有权者承诺。',['M11','M39','M40'])
        result['questions'].append({'field':'decision_authority','question':FACT_QUESTIONS['decision_authority']})
    if facts.get('can_change_scope') is False:
        hard('H08','保留已核原范围，不提出减项、新套餐或改变旧约的试点。',['M11','M17'])
    if '免费索取' in types: need('paid_obligation')
    if '投诉冲突' in types and not listening: need('existing_terms_known')
    if '报价嫌贵' in types: need('price_known');need('scope_known')
    if '犹豫拖延' in types or '复购转介绍' in types: need('contact_preference')
    if '效果保证' in types: need('delivery_capability')
    if listening:
        hard('H06','对方只要求倾听：承接感受，不主动推销、布置执行步骤或强行分析。',['M05','M06'])

    a=[];b=[]
    def add(target, mids):
        for m in mids:
            if m not in target:target.append(m)
    if stop:
        add(a,['M10','M18'] if duty else ['M10'])
        if duty:add(b,['M01','M11','M39'])
        result['excluded'].append({'methods':['M20','M21','M22','M43'],'reason':'联系偏好阻止主动营销；必要服务单列'})
    elif listening:
        add(a,['M06']);add(b,['M05'])
        if duty:add(a,['M18']);add(b,['M18'])
    elif insufficient:
        if duty:add(a,['M01','M18']);add(b,['M18','M10'])
        if facts.get('direct_price_request') is True:add(a,['M17']);add(b,['M17'])
        add(a,['M04','M36','M18']);add(b,['M01','M40'])
        result['excluded'].append({'methods':['M43'],'reason':'能力或资金未满足，不生成逼单路线'})
    else:
        if duty:add(a,['M01','M30','M18']);add(b,['M10','M11'])
        if facts.get('direct_price_request') is True:add(a,['M17','M35']);add(b,['M17','M04'])
        for t in types:
            if duty and t in ('复购转介绍','免费索取','犹豫拖延'):continue
            add(a,ROUTES[t]['a']);add(b,ROUTES[t]['b'])
    # Direct price and original obligations remain compulsory. Defer secondary
    # tasks visibly instead of concatenating every recalled method.
    if facts.get('direct_price_request') is True and not listening and not stop:
        a=['M17']+[m for m in a if m!='M17']
        b=['M17']+[m for m in b if m!='M17']
    if duty:
        for group in (a,b):
            if 'M18' in group:group.remove('M18')
            group.insert(1 if group and group[0]=='M17' else 0,'M18')
    result['deferred_methods']=list(dict.fromkeys(a[4:]+b[4:]))
    result['sequencing']='先处理原有责任与当前明确问题；每方案至多4个方法，其余保留为后续待检索任务。'
    a=a[:4];b=b[:4]
    active=set(a+b)
    for t in library['tensions']:
        if len(set(t['methods'])&active)>=2 or (t['id']=='K04' and (stop or '犹豫拖延' in types)):
            result['conflict_resolutions'].append({'id':t['id'],'title':t['title'],'kind':t['kind'],
                'source_sides':t['sides'],'resolution':t['policy'],'nature':'分析者应用裁决，原文冲突不消失'})

    for name,mids in [('A',a),('B',b)]:
        if not mids:continue
        if listening:
            objective='简短复述感受，保留必要责任并停止推销' if name=='A' else '少说并留出表达空间，保留必要责任'
            condition='对方当前只希望倾听；不强迫分析或作购买决定；如有旧约责任继续按约处理'
        elif stop:
            objective='确认停止营销，并按原约处理必要责任' if name=='A' else '将未决责任交有权限者书面核实并安排交接'
            condition='仅在必要服务/争议处理范围内沟通；没有原有义务时不再主动联系'
        elif insufficient:
            objective='明确当前不适配，暂停购买推进' if name=='A' else '先补事实与能力，设置不依赖购买的内部验证'
            condition='不安排借贷购买，不售卖尚不具备的服务；B不承诺试点收益'
        else:
            objective='回应当前问题，在现有范围内提出下一步' if name=='A' else '降低承诺或先验证，再决定是否扩大'
            condition='满足所选方法前提；任何报价、套餐、时间与权限须来自已核事实'
        actions=[]
        for mid in mids:
            card=cards[mid]
            # The selected micro-action has a real method source. A/B deliberately
            # use different portions rather than duplicate the whole rule.
            if listening:
                texts=['复述对方已经表达的感受，留出继续说或暂停的空间；不自动提问、建议或推销。'] if name=='A' else ['表示愿意听，等待对方决定是否继续；不主动要求拆解事件或采取行动。']
                if mid=='M18':texts=['已有服务、退款或其他责任继续按原约处理，不以此刻讨论或购买为条件；此刻不强迫对方进入分析。']
                nature='依据方法的分析者场景改写'
            elif mid=='M17':
                if facts.get('price_known') is True:
                    texts=['先提供已核真实价格或计价依据，不增加未确认的折扣或套餐；同时说明已核范围和不包含项。']
                else:
                    texts=['明确说明价格尚未核定，先核实真实价格/计价条件；不补造数字，不以塑品回避问价。']
                if facts.get('scope_known') is not True:texts.append('当前交付范围仍待核，在核清前不发出最终报价承诺。')
                if name=='B':
                    texts.append('保留已核原范围与报价，不提出减项或新套餐；允许暂停。' if facts.get('can_change_scope') is False else '只有确实存在且获授权的减项方案才比较范围；否则保留原报价并允许暂停。')
                nature='基于明确问价与事实状态的应用动作'
            elif duty and mid=='M18':
                texts=['核对并按原约处理已购权益、未完成交付及退款请求；不能要求续费、好评、转介绍或先认错作为处理前提。',
                       '条款或权限不明时记录具体争议并交有权限者核实，给经确认的处理安排；不捏造退款已办或处理期限。']
                nature='既有责任优先的应用动作'
            elif stop and duty:
                texts=['只处理已有服务、结算或必要交接，按对方允许的渠道及原有约定沟通；停止主动营销和新增合作邀请。']
                nature='基于停止营销及原有责任的应用约束'
            elif stop and not duty:
                texts=['记录停止营销，不再追加联系或诱导购买；若对方另行提出必要服务问题再按原约处理。']
                nature='基于明确联系偏好的应用约束'
            elif insufficient and name=='B':
                texts=['先记录条件缺口，只验证已有事实和自身交付能力；不建议客户购买或借贷试跑。']
                nature='基于能力/预算限制的应用约束'
            elif duty and mid in ('M10','M11','M39'):
                texts=['书面列明原有范围、未完成事项与各方责任；核实后按原约处理或交接，不引入新合作试点或额外付费条件。']
                nature='基于旧约责任的应用约束'
            else:
                selected_steps=card['steps'][:2] if name=='A' else card['steps'][-2:]
                texts=[x['text'] for x in selected_steps]
                nature='分析者操作化；需结合本次硬约束'
            if not listening and mid in ('M11','M39','M40') and facts.get('can_change_scope') is False:
                texts=['保留已核原约和交付范围，只核实责任、依赖及执行状态；不设计改变范围的新合作试点。']
                nature='依据不可变更范围的应用动作'
            if not listening and mid=='M04' and facts.get('can_change_scope') is False:
                texts=['核对当前原范围与需求、能力是否匹配；若不匹配则暂停或不接，不缩小或扩大约定范围。']
                nature='依据不可变更范围的适配动作'
            if not listening and facts.get('decision_authority') is False and mid in ('M11','M39','M40'):
                texts=['整理现有事实与待确认事项，提交有权者批准；在批准前不确定新结算、排期、范围或启动试点。']
                nature='依据权限缺口的待审批动作'
            actions.append({'method':mid,'title':card['title'],'actions':texts,'nature':nature,
                'evidence':card['representative_evidence'],'preconditions':[x['text'] for x in card['preconditions']],
                'exceptions':[x['text'] for x in card['exceptions']],
                'confidence':card['operational_confidence'],'outcome_evidence':card['effectiveness']})
        result['candidates'].append({'id':name,'objective':objective,'applicability':condition,'method_ids':mids,
            'steps':actions,
            'cost':'需要核事实和完成当前责任；沟通量按对方偏好限制' if name=='A' else '通常多一轮内部核实/试点或等待；时间成本由用户决定是否接受',
            'tradeoff':'更快回应当前任务，但前提或能力不明时不得直接推进' if name=='A' else '减少新增承诺与信息风险，可能延后交易；未证明比A效果更好',
            'stop_condition':'明确拒绝、权益/权限冲突或关键事实无法核实则停止相应动作；原有责任仍按约处理',
            'verification':['是否回答当前问题','是否使用真实事实并标未知','是否满足原有责任与联系偏好','下一步是否获得适当同意']})
    result['differences']=[{'type':t,'comparison':ROUTES[t]['difference']} for t in types]
    if stop:result['differences']=[{'type':'联系约束优先','comparison':('在停止营销和保留旧义务前提下，A轻量复述感受，B少说留出表达空间；不强迫现在讨论解决方案。' if listening else 'A收尾并处理已有服务；B仅在确有未决责任时进行授权核实/交接。不存在继续营销的B。')}]
    elif listening:result['differences']=[{'type':'倾听优先','comparison':'A轻量复述感受；B少说并留出表达空间。两者都不主动推销或布置任务；原有责任继续履行。'}]
    elif insufficient:result['differences']=[{'type':'适配优先','comparison':'A明确当前不接或不推进；B内部补事实与能力后再评估。两者都不以借贷购买检验方法。'}]
    if facts.get('decision_authority') is False:
        result['differences'].append({'type':'权限覆盖','comparison':'两个候选均只是提交有权者的草案，不是已批准执行的合作或结算方案。'})
    if facts.get('can_change_scope') is False:
        if not stop and not listening and not insufficient:
            result['differences']=[{'type':'原范围内比较','comparison':'A回答现有范围和安排；B核实剩余条件或暂停。两者都不设计范围变更或小试点；报价、旧约与权限按已核事实保留。'}]
            if facts.get('decision_authority') is False:
                result['differences'].append({'type':'权限覆盖','comparison':'两个候选均只提交有权者确认，当前不作执行承诺。'})
        result['differences'].append({'type':'范围覆盖','comparison':'两个候选均保留原范围；原先减项/试点路线不适用，只能比较回应、核实或暂停。'})
    if listening:
        result['deferred_questions']=result['questions']
        result['questions']=[]
    if result['questions']:result['status']='conditional'
    if stop and not duty:result['status']='closed_for_marketing'
    elif insufficient:result['status']='no_current_sales_plan'
    if len(result['candidates'])<2:
        result['alternative_limit']='只有一个符合当前约束的路径，不为凑方案B继续营销。'
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',required=True,type=Path)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    payload=json.loads(args.input.read_text('utf-8-sig'))
    result=plan(payload)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        # The reference engine must not overwrite source or Skill resources.
        target=args.output.resolve()
        if target==args.input.resolve() or target==Path(__file__).resolve() or ROOT.resolve() in target.parents:
            raise ValueError('Output must be outside the Skill and different from input')
        if 'L1-原始层封存-P2.71' in target.parts:
            raise ValueError('Output cannot target frozen L1')
        if target.exists():raise FileExistsError(f'Refuse to overwrite result: {target}')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(text,'utf-8')
    else:print(text,end='')


if __name__=='__main__':
    main()
