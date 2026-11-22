# 接口

模块GET使用仓内样例，模块POST可传csv或rows与context，直接计算当前规则。/api/runs使用完整流水线并原子保存。每个阶段返回rows、quarantine、metrics；后续阶段还返回累计隔离。/api/upload接收multipart文件file。/api/runs/<id>/archive只导出一份带清单与证据的CSV。

## 钢筋净量裁决（M8，独立域 domain=rebar）

- `GET/POST /api/rebar`：预览裁决，不落库；POST可传sample、csv与parameters。
- `POST /api/rebar/runs`：完整裁决并幂等保存，同源同参数复用同一run_id。
- `GET /api/rebar/runs`：钢筋域批次历史。
- `POST /api/rebar/runs/<id>/review`：body含version与decision（已复核/退回复核）。
- `POST /api/rebar/runs/<id>/publish`：body含version；`simulate_failure:true`返回409 PUBLISH_FAILED且事务回滚，版本与决策保持旧版。成功后version+1、决策置已发布，陈旧version返回409 STALE_VERSION。
- `POST /api/rebar/upload`：multipart字段file，4MB上限。
- `GET /api/runs/<id>/archive`：证据CSV含accepted、quarantine、carry_forward三类kind，来源行以_sources物理行号保留。

裁决结果另含carry_forward（待补依据结转）、lineage（逐行去向：accepted/over_cap/waste/misdelivery/pending_evidence）、cap_basis（图纸净量、已批变更量与上限）。
