import time
from app.config import ROOT,REBAR_DEFAULT_PARAMS
from app.errors import DomainError
from app.manifest import digest,manifest
from app import store
from app.modules.m8_rebar.rules import evaluate as adjudicate
REBAR_SAMPLE="rebar.csv"
def load_sample(name):
    if name!=REBAR_SAMPLE:raise DomainError("BAD_SAMPLE","样例不存在",404)
    return (ROOT/"sample_data"/name).read_bytes()
def calculate(raw,params=None):
    params=params or {}
    merged={**REBAR_DEFAULT_PARAMS,**params}
    started=time.monotonic()
    result=adjudicate(raw,{"parameters":merged,"quarantine":[]},merged)
    run_id="rebar-"+digest(raw,merged)[:20]
    payload={"run_id":run_id,"domain":"rebar","stages":[result],"manifest":manifest(raw,merged,started),
             "parameters":merged,"decision_detail":{"published":False}}
    return payload
def execute(raw,params=None):
    payload=calculate(raw,params)
    return store.save(payload["run_id"],payload,domain="rebar")
