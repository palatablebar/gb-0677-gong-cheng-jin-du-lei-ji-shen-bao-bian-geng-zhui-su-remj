from flask import render_template
from app.config import MODULES,TITLE,SHORT
from app.pipeline import execute,load_sample
from app import store,rebar_pipeline
def register_pages(app):
    def page(index):
        run=store.latest(domain="claim") or execute(load_sample("dirty.csv"))
        stage=run["stages"][index]
        rows=stage["rows"]
        columns=[['claim_id', 'item', 'period', 'cumulative_qty', 'previous_qty', 'change_id', 'reported'], ['claim_id', 'item', 'unit', 'cumulative_qty', 'previous_qty'], ['claim_id', 'period', 'approved_change', 'unit_price'], ['claim_id', 'period', 'cumulative_qty', 'approved_previous', 'increment_qty', 'gross_amount'], ['claim_id', 'item', 'gross_amount', 'retention', 'advance_recovery', 'expected'], ['claim_id', 'item', 'expected', 'reported', 'difference', 'status'], ['claim_id', 'period', 'expected', 'status']][index]
        labels={'claim_id': '申报编号', 'item': '清单项', 'period': '申报周期', 'cumulative_qty': '本次累计量', 'previous_qty': '前审累计量', 'change_id': '变更单', 'reported': '申报净额', 'unit': '单位', 'approved_change': '已批变更', 'unit_price': '单价 / 元', 'approved_previous': '修订前审量', 'increment_qty': '本期工程量', 'gross_amount': '本期总额', 'retention': '质保金', 'advance_recovery': '预付款扣回', 'expected': '实算净额', 'difference': '净额差异', 'status': '结论', 'gross_total': '本期总额合计', 'net_total': '实算净额合计'}
        for key,label in {'accepted_inputs': '采纳来源行', 'quarantine_inputs': '隔离来源行', 'output_records': '结果记录', 'input': '输入行', 'excluded': '排除行', 'balanced': '行数平衡', 'expected_total': '预期合计', 'reported_total': '申报合计', 'differences': '差异项', 'blank': '空行', 'repeated_headers': '分段表头', 'encoding': '编码', 'duplicate': '重复行', 'quarantine': '隔离行', 'accepted': '采纳行', 'sha256': '校验摘要', 'ready': '可归档'}.items(): labels.setdefault(key,label)
        return render_template(f"m{index+1}.html",title=TITLE,short=SHORT,modules=MODULES,index=index,run=run,stage=stage,rows=rows,columns=columns[:12],history=store.history(),labels=labels)
    def rebar_page():
        run=store.latest(domain="rebar") or rebar_pipeline.execute(rebar_pipeline.load_sample("rebar.csv"))
        stage=run["stages"][0]
        columns=[["batch_no","item","period","issue_qty","admitted_qty","basis_drawing_qty","basis_change_qty","basis_change_id","excess_qty","cap_total"]]
        labels={'batch_no':'领料批次','item':'清单项','period':'周期','issue_qty':'领料量/t','admitted_qty':'计入净量/t','basis_drawing_qty':'图纸净量依据/t','basis_change_qty':'变更依据/t','basis_change_id':'变更单号','excess_qty':'超限隔离/t','cap_total':'净量上限/t'}
        return render_template("m8.html",title=TITLE,short=SHORT,modules=MODULES,index=7,run=run,stage=stage,
                               rows=stage["rows"],columns=columns[0],history=store.history(domain="rebar"),labels=labels)
    app.add_url_rule("/",view_func=lambda:page(4))
    for index,(slug,name) in enumerate(MODULES):
        if slug=="rebar":continue
        app.add_url_rule("/"+slug,endpoint="page_"+slug,view_func=lambda index=index:page(index))
    app.add_url_rule("/rebar",endpoint="page_rebar_workbench",view_func=rebar_page)
