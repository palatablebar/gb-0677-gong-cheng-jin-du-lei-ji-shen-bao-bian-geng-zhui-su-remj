import csv,io
import pytest
from app.config import REBAR_COLUMNS
from app.errors import DomainError
from app import rebar_pipeline,store
from app.modules.m8_rebar.rules import evaluate
from app.modules.m8_rebar import intake
def load_rebar():return rebar_pipeline.load_sample("rebar.csv")
HEADER=",".join(REBAR_COLUMNS)
def row(batch,item="钢筋",period="2026-11",qty="10",nature="净料",change="",note=""):
    return f"{batch},{item},{period},{qty},{nature},{change},{note}"
def run(csv_text,params=None):
    base={"previous_approved_net":{"001":"0"}}
    base.update(params or {})
    return evaluate(csv_text.encode(),{"parameters":base,"quarantine":[]})
def test_real_sample_unique_signable_quantity():
    "图纸95+已批变更5=上限100；前审75；本期唯一可签=100-75=25"
    r=evaluate(load_rebar(),{"parameters":{},"quarantine":[]})
    m=r["metrics"]
    assert m["current_period_net_total"]=="25"
    assert m["certified_net_total"]=="100"
    assert m["signable"]["001"]["cap"]["cap_total"]=="100"
    assert m["signable"]["001"]["current_period_net"]=="25"
def test_waste_and_misdelivery_never_enter_net():
    csv_text="\n".join([HEADER,row("A",qty="90"),row("W",qty="8",nature="损耗"),row("M",qty="4",nature="错发")])
    r=run(csv_text)
    assert sum(1 for q in r["quarantine"] if q["reason"]=="REBAR_WASTE")==1
    assert sum(1 for q in r["quarantine"] if q["reason"]=="REBAR_MISDELIVERY")==1
    assert r["metrics"]["certified_net_total"]=="90"
    assert {x["batch_no"] for x in r["rows"]}=={"A"}
def test_over_cap_split_keeps_single_traceable_record():
    "净料90+净料20，上限100：第二笔只认10，10隔离，来源行保留"
    csv_text="\n".join([HEADER,row("A",qty="90"),row("B",qty="20")])
    r=run(csv_text)
    b=next(x for x in r["rows"] if x["batch_no"]=="B")
    assert b["admitted_qty"]=="10" and b["excess_qty"]=="10"
    over=[q for q in r["quarantine"] if q["reason"]=="OVER_CAP_NET"]
    assert len(over)==1 and over[0]["_sources"]==b["_sources"]
    assert r["metrics"]["certified_net_total"]=="100"
def test_retry_batch_is_not_accumulated_twice():
    once="\n".join([HEADER,row("A",qty="20")])
    twice="\n".join([HEADER,row("A",qty="20"),row("A",qty="20")])
    r1=run(once);r2=run(twice)
    assert r1["metrics"]["certified_net_total"]==r2["metrics"]["certified_net_total"]=="20"
    assert r2["metrics"]["retry_batches"]==1
    assert any(q["reason"]=="DUPLICATE_BATCH" for q in r2["quarantine"])
def test_conflicting_retry_is_quarantined_not_overwritten():
    csv_text="\n".join([HEADER,row("A",qty="20"),row("A",qty="99")])
    r=run(csv_text)
    assert r["metrics"]["certified_net_total"]=="20"
    assert any(q["reason"]=="DUPLICATE_CONFLICT" for q in r["quarantine"])
def test_pending_evidence_carries_forward_with_source():
    csv_text="\n".join([HEADER,row("A",qty="10"),row("B",qty="6",note="依据待补")])
    r=run(csv_text)
    assert r["metrics"]["certified_net_total"]=="10"
    assert r["metrics"]["pending_evidence_carry"]==1
    c=r["carry_forward"][0]
    assert c["batch_no"]=="B" and c["_sources"] and c["carry_qty"]=="6"
    assert any(q["reason"]=="PENDING_EVIDENCE" and q["_line"]==c["_line"] for q in r["quarantine"])
def test_approved_change_extends_cap_draft_does_not():
    csv_text="\n".join([HEADER,row("A",qty="103")])
    r=run(csv_text)
    assert r["metrics"]["certified_net_total"]=="100"
    basis=next(x for x in r["rows"] if x["batch_no"]=="A")
    assert basis["basis_drawing_qty"]=="95" and basis["basis_change_qty"]=="5" and basis["basis_change_id"]=="C2"
    catalog={c["change_id"]:c for c in r["metrics"]["change_basis"]}
    assert catalog["C2"]["_effective_for_period"] is True
    assert catalog["C3"]["_effective_for_period"] is False
def test_draft_change_qty_param_is_rejected():
    csv_text="\n".join([HEADER,row("A",qty="10")])
    r=run(csv_text,{"approved_change_qty":{"C3":"8"}})
    assert any(q["reason"]=="CHANGE_NOT_EFFECTIVE" for q in r["quarantine"])
def test_lineage_conservation_real_sample():
    r=evaluate(load_rebar(),{"parameters":{},"quarantine":[]})
    assert r["metrics"]["lineage_balanced"] is True
    decided={x["line"] for x in r["lineage"]}|{q.get("_line",0) for q in r["quarantine"] if q.get("_line",0)>0}
    assert all(line>0 for line in decided)
def test_re_aggregation_keeps_every_source_line():
    "重新归集不丢来源：所有物理行都能在lineage或隔离中追溯"
    raw=load_rebar()
    r=evaluate(raw,{"parameters":{},"quarantine":[]})
    stage=intake.evaluate(raw)
    physical={x["_line"] for x in stage["rows"]}|{x["_line"] for x in stage["quarantine"]}
    traced={x["line"] for x in r["lineage"]}|{q.get("_line",0) for q in r["quarantine"] if q.get("_line",0)>0}
    assert physical<=traced
def test_bad_period_row_is_quarantined():
    csv_text="\n".join([HEADER,row("A",period="2026-10",qty="10")])
    r=run(csv_text)
    assert any(q["reason"]=="BAD_PERIOD" for q in r["quarantine"])
def test_unknown_nature_and_item_rejected():
    csv_text="\n".join([HEADER,row("A",nature="代购"),row("B",item="999")])
    r=run(csv_text)
    reasons={q["reason"] for q in r["quarantine"]}
    assert "UNKNOWN_NATURE" in reasons and "UNKNOWN_ITEM" in reasons
def test_negative_increment_needs_reversal():
    csv_text="\n".join([HEADER,row("A",qty="10")])
    with pytest.raises(DomainError) as e:
        run(csv_text,{"previous_approved_net":{"001":"80"}})
    assert e.value.code=="NEGATIVE_INCREMENT"
def test_intake_three_empty_states():
    for raw,code in [(b"","EMPTY_FILE"),(b"\n","BLANK_ONLY"),(HEADER.encode(),"HEADER_ONLY")]:
        with pytest.raises(DomainError) as e:intake.evaluate(raw)
        assert e.value.code==code
def test_bad_header_rejected():
    with pytest.raises(DomainError) as e:intake.evaluate(b"a,b,c\n")
    assert e.value.code=="BAD_HEADER"
def test_api_idempotent_run_and_retry_no_double_accumulation(client):
    a=client.post("/api/rebar/runs",json={"sample":"rebar.csv"})
    assert a.status_code==200
    b=client.post("/api/rebar/runs",json={"sample":"rebar.csv"})
    assert b.get_json()["run_id"]==a.get_json()["run_id"]
    assert len(store.history(domain="rebar"))==1
    m=a.get_json()["stages"][0]["metrics"]
    assert m["retry_batches"]==1 and m["current_period_net_total"]=="25"
def test_api_publish_failure_restores_old_version(client):
    p=client.post("/api/rebar/runs",json={"sample":"rebar.csv"}).get_json()
    rid=p["run_id"]
    r=client.post(f"/api/rebar/runs/{rid}/publish",json={"version":1,"simulate_failure":True})
    assert r.status_code==409 and r.get_json()["code"]=="PUBLISH_FAILED"
    kept=store.get(rid)
    assert kept["version"]==1 and kept["decision"]=="待复核"
def test_api_publish_then_stale_version_rejected(client):
    p=client.post("/api/rebar/runs",json={"sample":"rebar.csv"}).get_json()
    rid=p["run_id"]
    assert client.post(f"/api/rebar/runs/{rid}/publish",json={"version":1}).status_code==200
    again=client.post(f"/api/rebar/runs/{rid}/publish",json={"version":1})
    assert again.status_code==409 and again.get_json()["code"]=="STALE_VERSION"
def test_api_review_and_archive_keep_sources(client):
    p=client.post("/api/rebar/runs",json={"sample":"rebar.csv"}).get_json()
    rid=p["run_id"]
    assert client.post(f"/api/rebar/runs/{rid}/review",json={"version":1,"decision":"已复核"}).status_code==200
    export=client.get(f"/api/runs/{rid}/archive")
    rows=list(csv.reader(io.StringIO(export.data.decode("utf-8-sig"))))
    kinds={x[3] for x in rows[1:]}
    assert {"accepted","quarantine","carry_forward"}<=kinds
    quarantined=[x for x in rows[1:] if x[3]=="quarantine"]
    assert any("REBAR_WASTE" in x[5] for x in quarantined)
    assert any("DUPLICATE_BATCH" in x[5] for x in quarantined)
def test_api_preview_and_page(client):
    assert client.get("/api/rebar").status_code==200
    page=client.get("/rebar")
    assert page.status_code==200 and "本期唯一可签认钢筋净工程量".encode() in page.data
def test_re_aggregation_with_corrected_params_makes_new_batch_without_losing_sources(client):
    first=client.post("/api/rebar/runs",json={"sample":"rebar.csv"}).get_json()
    second=client.post("/api/rebar/runs",json={"sample":"rebar.csv","parameters":{"drawing_net_qty":{"001":"110"}}}).get_json()
    assert first["run_id"]!=second["run_id"]
    assert len(store.history(domain="rebar"))==2
    raw=load_rebar()
    stage=intake.evaluate(raw)
    physical={x["_line"] for x in stage["rows"]}|{x["_line"] for x in stage["quarantine"]}
    s=second["stages"][0]
    traced={x["line"] for x in s["lineage"]}|{q.get("_line",0) for q in s["quarantine"] if q.get("_line",0)>0}
    assert physical<=traced
