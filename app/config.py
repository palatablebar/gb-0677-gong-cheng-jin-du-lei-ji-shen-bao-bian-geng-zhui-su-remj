from pathlib import Path
import os
ROOT=Path(__file__).resolve().parent.parent
DATA_DIR=Path(os.environ.get("DATA_DIR", "/tmp/progressclaim"))
TITLE='工程进度累计申报与变更追溯'
SHORT='progressclaim'
COLUMNS=['claim_id', 'item', 'period', 'cumulative_qty', 'previous_qty', 'change_id', 'reversal', 'reported', 'note']
MODULES=[('claims', '申报采信'), ('billitems', '清单映射'), ('changes', '变更定版'), ('increment', '累计还原'), ('deductions', '扣回核算'), ('valuation', '进度对账'), ('certificates', '签证归档'), ('rebar', '钢筋净量裁决')]
RULE_VERSION="2026.11.17-r1"
REBAR_COLUMNS=['batch_no','item','period','issue_qty','issue_nature','change_id','note']
REBAR_ITEMS={"钢筋":"001","001":"001"}
REBAR_NATURES={"净料":"net","net":"net","净量":"net","损耗":"waste","waste":"waste","错发":"misdelivery","misdelivery":"misdelivery"}
REBAR_DEFAULT_PARAMS={"period":"2026-11","drawing_net_qty":{"001":"95"},"approved_change_qty":{"C2":"5"},"previous_approved_net":{"001":"75"},"changes":[{"change_id":"C2","approved":True,"effective":"2026-11","qty":"5","note":"图纸会审增加构造筋"},{"change_id":"C3","approved":False,"effective":"2026-12","qty":"8","note":"待批加固方案"}]}
