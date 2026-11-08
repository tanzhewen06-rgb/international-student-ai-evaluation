"""Current-case facts only; original checklist output count remains 5/3/4/5/4."""
import json,hashlib
from versions.v4_9.audit import prepare_audit_instructions as prepare_parents

SCENARIO_HASHES={'scenario_1':'61f58f34fdfb7947a2afe646ec3830d5f9ed20ad511d5c60a3b9f296f555e7a2','scenario_2':'335f358b42c634cbc33cbe67809ad0aa7519074ccb599d490179553368259bf8','scenario_3':'feef7c50a018aa76d636263f22af4049178bcb9596936b7ec584c766e3447782','scenario_4':'866fa999a7412450bdfc79f2204840794bf70fc362d3b65769d2af598d904ea0','scenario_5':'912b57e9aa61d6a43b7901bab44261c581b46127fed59329c88126d99cf8944f'}
CURRENT_FACTS={
    'scenario_1':{'known':['Payment 800; available for payment 500; correct shortfall 300, not 200.','Today Monday; due this Friday: four days, not ten.','Last time late payment was permitted; this time permission has not been obtained.','Cash shifts are a classmate suggestion; work has not started.','Mum sent less this month; room costs have not been fully explained to her.'],
        'unknown':['Reason for reduced funds or transfer timing; current extension; payment contact role; visa category; work authorization; job conditions.']},
    'scenario_2':{'known':['Two teammates laughed after an explanation attempt; the student does not know the cause.','Task list assigns slides; this does not establish a ban on speaking.','Student mostly understands written lab steps; unsure whether to ask for a speaking role.','Two teammates report group and individual-speaking marks; neither verifies policy; both could coexist.'],
        'unknown':['Cause of laughter; rubric and actual speaking requirements.'],'explicit_clarification':['The account does not establish accent mockery.']},
    'scenario_3':{'known':['Student said yeah maybe about visitors, meant uncertainty, and did not explicitly say no.','Their food was used; who used it is unknown.','They said they had not eaten, but did not explain ownership or ask others not to use their food.','Takeaway was offered; student is hungry now and avoids visitors in the kitchen.'],
        'unknown':['Housemates motives or actual interpretation; sharing/guest agreements; finances; available replacement food; takeaway ownership/cost/current availability.']},
    'scenario_4':{'known':['48 is the reported first-paper mark for this class; prior marks at home were usually good.','Student confuses rewording readings with an independent argument.','Student believes next paper is due in two weeks; an open page says tomorrow 5 p.m., but its class identity is uncertain.','Considering dropping this class; this is not a decision to leave university.','Setback undermines confidence; student asks not to receive another load of questions.'],
        'unknown':['Maximum/pass mark; course standing; verified deadline for this paper; withdrawal deadline and consequences.']},
    'scenario_5':{'known':['Two different classmates on different days replied busy.','One still sends memes sometimes.','Saturday plans discussed at a club gathering; no direct invitation.','Student stayed about ten minutes then left; the STUDENT leaves club messages unread.'],
        'unknown':['Classmates motives or actual availability; Saturday club/private status; deliberate exclusion; message contents.']}}

def prepare_audit_instructions(instructions,record,contract):
    sid=record['scenario_id']
    if hashlib.sha256(record['scenario_prompt'].encode('utf-8')).hexdigest()!=SCENARIO_HASHES.get(sid):raise ValueError('Current fact summary is not bound to this saved scenario.')
    body=prepare_parents(instructions,record,contract)
    return body+'\n## Current-case factual boundaries\nThese summarize only this exact saved scenario; they are not facts from calibration cases. Check the ENTIRE candidate against them before scoring.\n'+json.dumps(CURRENT_FACTS[sid],ensure_ascii=False,separators=(',',':'))+'\n'
