"""Typed presentation protocol only. Nothing is inferred, scheduled or executed."""
import json
import math
import re
import time

MAX_BYTES = 1024*1024
STATUSES = ('disconnected','idle','running','stopped','error')
EVENT_TYPES = ('forecast','abstain','skip','outcome','status')


def number(value,label,minimum=0,maximum=1):
    try:
        good = type(value) in (int,float) and math.isfinite(value) and minimum<=value<=maximum
    except OverflowError:
        good = False
    if not good:
        raise ValueError(f'{label} must be a finite number from {minimum} to {maximum}')
    return value


def text(value,label,limit=400):
    if not isinstance(value,str) or not 1<=len(value)<=limit or any(ord(c)<32 or 127<=ord(c)<=159 for c in value):
        raise ValueError(f'{label} must be nonempty plain text, <= {limit} characters, without terminal controls')
    return value


def decode(raw):
    def reject(s):raise ValueError('Nonfinite JSON numbers are forbidden')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('Duplicate JSON keys are forbidden')
            result[k]=v
        return result
    try:return json.loads(raw,parse_constant=reject,object_pairs_hook=pairs)
    except (json.JSONDecodeError,RecursionError,UnicodeError) as e:raise ValueError('Invalid UTF-8 JSON') from e


def keys(value,allowed,label):
    if not isinstance(value,dict) or set(value)-set(allowed):
        raise ValueError(f'{label} contains unknown fields or is not an object')


def validate_event(value,stream=False):
    keys(value,('schema','id','type','at','model','summary','p_up','decision','outcome','status'),'event')
    if stream and value.get('schema')!='prediction-cli-event-v1':raise ValueError('Expected prediction-cli-event-v1')
    if not stream and 'schema' in value:raise ValueError('Nested snapshot events do not need a schema field')
    event=dict(value)
    text(event.get('id'),'event id',80)
    if event.get('type') not in EVENT_TYPES:raise ValueError('Unknown event type')
    number(event.get('at'),'event at',0,4102444800)
    if type(event['at']) is not int:raise ValueError('event at must be UTC integer epoch seconds')
    text(event.get('model'),'model',80)
    if not re.fullmatch(r'[A-Za-z0-9._:-]{1,80}',event['model']):raise ValueError('Model identifiers must be single safe tokens')
    text(event.get('summary'),'summary',400)
    if 'p_up' in event and event['p_up'] is not None:number(event['p_up'],'p_up')
    if 'decision' in event and event['decision'] not in ('up','down','abstain'):raise ValueError('Invalid direction')
    if 'outcome' in event and event['outcome'] not in ('up','down','flat','void'):raise ValueError('Invalid observed outcome')
    if event['type']=='forecast' and (event.get('decision') not in ('up','down') or event.get('p_up') is None):raise ValueError('Forecast requires direction and p_up')
    if event['type']=='outcome' and event.get('outcome') not in ('up','down','flat','void'):raise ValueError('Outcome event requires observed outcome')
    if 'status' in event and event['status'] not in STATUSES:raise ValueError('Invalid backend status')
    return event


def empty_snapshot():
    return {'schema':'prediction-cli-snapshot-v1','symbol':'BTC/USD','horizon_seconds':900,'mode':'external','status':'disconnected','model':'unconfigured','models':[],
            'as_of':0,'metrics':{'forecast_score':None,'accuracy':None,'skipped':0},'events':[]}


def validate_snapshot(value):
    keys(value,('schema','symbol','horizon_seconds','mode','status','model','models','as_of','metrics','events'),'snapshot')
    if value.get('schema')!='prediction-cli-snapshot-v1':raise ValueError('Expected prediction-cli-snapshot-v1')
    if value.get('symbol')!='BTC/USD' or value.get('horizon_seconds')!=900:raise ValueError('Only educational BTC/USD 900-second forecasts are supported')
    if value.get('mode') not in ('external','synthetic'):raise ValueError('mode must be external or synthetic')
    if value.get('status') not in STATUSES:raise ValueError('Unknown backend status')
    text(value.get('model'),'model',80)
    if not re.fullmatch(r'[A-Za-z0-9._:-]{1,80}',value['model']):raise ValueError('Model identifiers must be single safe tokens')
    number(value.get('as_of'),'as_of',0,4102444800)
    if type(value['as_of']) is not int:raise ValueError('as_of must be UTC integer epoch seconds')
    models=value.get('models',[])
    if not isinstance(models,list) or len(models)>30:raise ValueError('models must be a list of <=30 declared identifiers')
    for m in models:
        text(m,'model',80)
        if not re.fullmatch(r'[A-Za-z0-9._:-]{1,80}',m):raise ValueError('Model identifiers must be single safe tokens')
    metrics=value.get('metrics')
    keys(metrics,('forecast_score','accuracy','skipped'),'metrics')
    for k in ('forecast_score','accuracy'):
        if metrics.get(k) is not None:number(metrics[k],k)
    if type(metrics.get('skipped')) is not int or not 0<=metrics['skipped']<=100000000:raise ValueError('skipped must be a nonnegative integer')
    events=value.get('events')
    if not isinstance(events,list) or len(events)>200:raise ValueError('Snapshot events must contain <=200 rows; rotate history externally')
    rows=[validate_event(e) for e in events]
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate event ids')
    return {**value,'models':models,'events':rows,'metrics':{'forecast_score':metrics.get('forecast_score'),'accuracy':metrics.get('accuracy'),'skipped':metrics['skipped']}}


def demo_snapshot():
    now=int(time.time())
    return validate_snapshot({'schema':'prediction-cli-snapshot-v1','symbol':'BTC/USD','horizon_seconds':900,'mode':'synthetic','status':'idle','model':'demo-mock','models':['demo-mock'],'as_of':now,
        'metrics':{'forecast_score':None,'accuracy':None,'skipped':1},'events':[
            {'id':'demo-1','type':'skip','at':now-60,'model':'demo-mock','summary':'Example: weak evidence, so the forecast was skipped.'},
            {'id':'demo-2','type':'status','at':now,'model':'demo-mock','summary':'Synthetic interface demo. No backend or model ran.'}]})
