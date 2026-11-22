from flask import Blueprint,request,jsonify
from app.config import REBAR_DEFAULT_PARAMS
from app.errors import DomainError
from app import rebar_pipeline,store
bp=Blueprint("rebar",__name__)
def _payload():
    payload=request.get_json(silent=True) if request.method=="POST" else {}
    if payload is None or not isinstance(payload,dict):raise DomainError("BAD_BODY","请求需要对象")
    return payload
def _raw(payload):
    if "csv" in payload and payload["csv"] is not None:
        if not isinstance(payload["csv"],str):raise DomainError("BAD_CSV","CSV需要文本")
        return payload["csv"].encode()
    return rebar_pipeline.load_sample(payload.get("sample","rebar.csv"))
@bp.route("/api/rebar",methods=["GET","POST"])
def preview():
    payload=_payload()
    params=payload.get("parameters",{})
    if not isinstance(params,dict):raise DomainError("BAD_PARAMETERS","参数需要对象")
    from app.modules.m8_rebar.rules import evaluate
    raw=_raw(payload)
    merged={**REBAR_DEFAULT_PARAMS,**params}
    return jsonify(evaluate(raw,{"parameters":merged,"quarantine":[]},merged))
@bp.route("/api/rebar/runs",methods=["POST"])
def runs():
    payload=_payload()
    params=payload.get("parameters",{})
    if not isinstance(params,dict):raise DomainError("BAD_PARAMETERS","参数需要对象")
    return jsonify(rebar_pipeline.execute(_raw(payload),params))
@bp.route("/api/rebar/runs",methods=["GET"])
def runs_history():
    return jsonify({"runs":store.history(domain="rebar")})
@bp.route("/api/rebar/upload",methods=["POST"])
def upload():
    f=request.files.get("file")
    if not f:raise DomainError("NO_FILE","请选择CSV文件")
    return jsonify(rebar_pipeline.execute(f.read()))
@bp.route("/api/rebar/runs/<run_id>/review",methods=["POST"])
def review(run_id):
    p=request.get_json(silent=True) or {}
    if not isinstance(p.get("version"),int):raise DomainError("BAD_VERSION","请提供版本号")
    return jsonify(store.review(run_id,p["version"],p.get("decision")))
@bp.route("/api/rebar/runs/<run_id>/publish",methods=["POST"])
def publish(run_id):
    p=request.get_json(silent=True) or {}
    if not isinstance(p.get("version"),int):raise DomainError("BAD_VERSION","请提供版本号")
    return jsonify(store.publish(run_id,p["version"],fail=bool(p.get("simulate_failure",False))))
