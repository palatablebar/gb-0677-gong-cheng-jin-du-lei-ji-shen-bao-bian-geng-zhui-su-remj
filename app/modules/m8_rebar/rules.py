from datetime import datetime
from decimal import Decimal
from app.config import REBAR_DEFAULT_PARAMS,REBAR_ITEMS,REBAR_NATURES
from app.values import number
from app.reasons import reject
from app.errors import DomainError
from app.modules.m8_rebar.intake import evaluate as intake
PENDING_NOTES={"依据待补","待补依据","净量依据待补"}
def _params(context):
    p=dict(REBAR_DEFAULT_PARAMS)
    p.update((context or {}).get("parameters",{}) or {})
    return p
def _decimal_map(defaults,overrides):
    merged={str(k):number(v) for k,v in (defaults or {}).items()}
    for k,v in (overrides or {}).items():merged[str(k)]=number(v)
    return merged
def _valid_period(period):
    try:return len(period)==7 and datetime.strptime(period,"%Y-%m") is not None
    except (ValueError,TypeError):return False
def _change_catalog(params,period):
    catalog=[]
    for rule in params.get("changes",[]):
        effective=bool(rule.get("approved")) and str(rule.get("effective",""))<=period
        catalog.append({"change_id":rule["change_id"],"approved":bool(rule.get("approved")),
                        "effective":rule.get("effective",""),"qty":str(number(rule["qty"])),
                        "note":rule.get("note",""),"_effective_for_period":effective})
    return catalog
def evaluate(raw_or_rows,context=None,params=None):
    context=context or {}
    if params is None:params=_params(context)
    else:params={**REBAR_DEFAULT_PARAMS,**params}
    period=str(params.get("period",""))
    if not _valid_period(period):raise DomainError("BAD_PERIOD","裁决周期需要YYYY-MM")
    if isinstance(raw_or_rows,(bytes,bytearray)):
        stage=intake(bytes(raw_or_rows),context)
        rows=stage["rows"];quarantine=list(stage["quarantine"]);intake_metrics=stage["metrics"]
    else:
        rows=list(raw_or_rows);quarantine=list(context.get("quarantine",[]));intake_metrics=context.get("intake")
    drawing=_decimal_map(params.get("drawing_net_qty",{}),params.get("drawing_net_qty_override",{}))
    previous=_decimal_map(params.get("previous_approved_net",{}),params.get("previous_approved_net_override",{}))
    change_qty=_decimal_map(params.get("approved_change_qty",{}),params.get("approved_change_qty_override",{}))
    catalog=_change_catalog(params,period)
    effective_ids={c["change_id"] for c in catalog if c["_effective_for_period"]}
    for cid,qty in change_qty.items():
        if cid not in effective_ids:
            quarantine.append(reject({"_line":-1,"_sources":[],"change_id":cid,"batch_no":cid},
                                     "CHANGE_NOT_EFFECTIVE",f"变更{cid}未批准或未在{period}生效，其量{qty}不进入净量上限"))
    item_changes={}
    for cid in effective_ids:
        q=change_qty.get(cid)
        if q is None:
            rule=next(c for c in catalog if c["change_id"]==cid);q=number(rule["qty"])
        item_changes.setdefault("001",[]).append((cid,q))
    items=set(drawing)|set(previous)|set(REBAR_ITEMS.values())
    pools={};cap_basis={}
    for item in items:
        d=drawing.get(item,Decimal(0))
        changes=item_changes.get(item,[])
        c=sum((q for _,q in changes),Decimal(0))
        pools[item]={"drawing_remaining":d,"change_remaining":list(changes)}
        cap_basis[item]={"drawing_net_qty":str(d),
                         "approved_change_qty":str(c),
                         "approved_change_ids":"/".join(cid for cid,_ in changes),
                         "cap_total":str(d+c)}
    good=[];carry=[];lineage=[];accepted_by_item={item:Decimal(0) for item in items}
    for row in sorted(rows,key=lambda r:(str(r.get("item","")),str(r.get("batch_no","")))):
        line=row.get("_line",0)
        if not _valid_period(row.get("period","")):
            quarantine.append(reject(row,"BAD_PERIOD","领料周期格式非法"));continue
        if row.get("period","")!=period:
            quarantine.append(reject(row,"BAD_PERIOD",f"非本期（{period}）领料，退回重新归集"));continue
        item=REBAR_ITEMS.get(row.get("item"))
        if item is None:
            quarantine.append(reject(row,"UNKNOWN_ITEM","清单项未登记"));continue
        nature=REBAR_NATURES.get(row.get("issue_nature"))
        if nature is None:
            quarantine.append(reject(row,"UNKNOWN_NATURE","领料性质未登记（仅认净料/损耗/错发）"));continue
        try:qty=number(row["issue_qty"])
        except DomainError as e:
            quarantine.append(reject(row,e.code,e.message));continue
        if qty<=0:
            quarantine.append(reject(row,"BAD_QTY","领料量必须为正"));continue
        pools.setdefault(item,{"drawing_remaining":Decimal(0),"change_remaining":[]})
        cap_basis.setdefault(item,{"drawing_net_qty":"0","approved_change_qty":"0","approved_change_ids":"","cap_total":"0"})
        accepted_by_item.setdefault(item,Decimal(0))
        if nature=="waste":
            quarantine.append(reject(row,"REBAR_WASTE",f"损耗{qty}t隔离，不进入正式工程量"))
            lineage.append({"line":line,"batch_no":row["batch_no"],"item":item,"bucket":"waste","qty":str(qty)});continue
        if nature=="misdelivery":
            quarantine.append(reject(row,"REBAR_MISDELIVERY",f"错发{qty}t隔离，不进入正式工程量"))
            lineage.append({"line":line,"batch_no":row["batch_no"],"item":item,"bucket":"misdelivery","qty":str(qty)});continue
        if nature=="net" and str(row.get("note","")).strip() in PENDING_NOTES:
            carry.append({**row,"item":item,"_adjudication":"pending_evidence","carry_qty":str(qty),
                          "reason":"PENDING_EVIDENCE","detail":"已安装但未补齐净量依据，结转下期，本期不签认"})
            quarantine.append(reject(row,"PENDING_EVIDENCE","已安装但未补齐净量依据，结转下期，本期不签认"))
            lineage.append({"line":line,"batch_no":row["batch_no"],"item":item,"bucket":"pending_evidence","qty":str(qty)});continue
        pool=pools[item];need=qty;basis_drawing=Decimal(0);basis_change=Decimal(0);used_changes=[]
        take=min(need,pool["drawing_remaining"])
        basis_drawing+=take;pool["drawing_remaining"]-=take;need-=take
        for cid,remaining in list(pool["change_remaining"]):
            if need<=0:break
            take=min(need,remaining)
            basis_change+=take;need-=take;used_changes.append(cid)
            pool["change_remaining"].remove((cid,remaining));pool["change_remaining"].append((cid,remaining-take))
        admitted=qty-need;over=need
        if admitted>0:
            good.append({**row,"item":item,"issue_nature":"net","admitted_qty":str(admitted),
                         "excess_qty":str(over),"basis_drawing_qty":str(basis_drawing),
                         "basis_change_qty":str(basis_change),
                         "basis_change_id":"/".join(used_changes),
                         "cap_total":cap_basis[item]["cap_total"],"_adjudication":"accepted"})
            accepted_by_item[item]+=admitted
            lineage.append({"line":line,"batch_no":row["batch_no"],"item":item,"bucket":"accepted",
                            "qty":str(admitted),"drawing":str(basis_drawing),"change":str(basis_change),
                            "change_ids":"/".join(used_changes)})
        if over>0:
            quarantine.append(reject({**row,"admitted_qty":str(admitted)},"OVER_CAP_NET",
                                     f"净料{qty}t中{over}t超出图纸净量+已批变更上限{cap_basis[item]['cap_total']}t，隔离不签"))
            lineage.append({"line":line,"batch_no":row["batch_no"],"item":item,"bucket":"over_cap","qty":str(over)})
    signable={}
    for item in sorted(set(pools)|set(previous)):
        prev=previous.get(item,Decimal(0));cumulative=accepted_by_item.get(item,Decimal(0))
        period_qty=cumulative-prev
        if period_qty<0:
            raise DomainError("NEGATIVE_INCREMENT",f"项{item}累计签认净量{cumulative}低于前审{prev}，需冲回凭证")
        signable[item]={"previous_approved_net":str(prev),"cumulative_certified_net":str(cumulative),
                        "current_period_net":str(period_qty),"cap":cap_basis.get(item,{})}
    accepted_lines={x["line"] for x in lineage if x["bucket"]=="accepted"}
    quarantine_lines={q.get("_line",0) for q in quarantine if q.get("_line",0) and q.get("_line",0)>0}
    retry_lines={q.get("_line",0) for q in quarantine if q.get("reason")=="DUPLICATE_BATCH" and q.get("_line",0)>0}
    metrics={"period":period,
             "input":intake_metrics["input"] if intake_metrics else len(rows)+len(quarantine),
             "net_batches":sum(1 for r in rows if REBAR_NATURES.get(r.get("issue_nature"))=="net"),
             "waste_quarantine":sum(1 for q in quarantine if q.get("reason")=="REBAR_WASTE"),
             "misdelivery_quarantine":sum(1 for q in quarantine if q.get("reason")=="REBAR_MISDELIVERY"),
             "over_cap_quarantine":sum(1 for q in quarantine if q.get("reason")=="OVER_CAP_NET"),
             "pending_evidence_carry":len(carry),
             "retry_batches":len(retry_lines),
             "accepted_lines":len(accepted_lines),
             "quarantine_lines":len(quarantine_lines),
             "lineage_balanced":_line_balance(intake_metrics,lineage,quarantine),
             "signable":signable,"change_basis":catalog,
             "certified_net_total":str(sum((Decimal(v["cumulative_certified_net"]) for v in signable.values()),Decimal(0))),
             "current_period_net_total":str(sum((Decimal(v["current_period_net"]) for v in signable.values()),Decimal(0))),
             "ready":True}
    return {"rows":good,"quarantine":quarantine,"carry_forward":carry,"lineage":lineage,
            "cap_basis":cap_basis,"metrics":metrics}
def _line_balance(intake_metrics,lineage,quarantine):
    if not intake_metrics:return True
    decided={x["line"] for x in lineage}|{q.get("_line",0) for q in quarantine if q.get("_line",0)>0}
    decided={line for line in decided if line>0}
    excluded=intake_metrics["blank"]+intake_metrics["repeated_headers"]
    expected=intake_metrics["input"]-excluded
    return len(decided)==expected
