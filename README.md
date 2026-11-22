# 工程进度累计申报与变更追溯

供总包项目计量审核员核对原始记录、处理差异并封存证据。

## 启动

```sh
docker compose up --build -d
docker compose exec -T app pytest -q
```

打开 http://localhost:18246 。首次进入自动运行仓内脏样例。工具条可重跑、切换样例或上传CSV。SQLite保存在命名卷records中，重建服务保留批次。

## 模块

- 1. 申报采信：`/claims`，`/api/claims`。
- 2. 清单映射：`/billitems`，`/api/billitems`。
- 3. 变更定版：`/changes`，`/api/changes`。
- 4. 累计还原：`/increment`，`/api/increment`。
- 5. 扣回核算：`/deductions`，`/api/deductions`。
- 6. 进度对账：`/valuation`，`/api/valuation`。
- 7. 签证归档：`/certificates`，`/api/certificates`。
- 8. 钢筋净量裁决：`/rebar`，`/api/rebar`。

## 核心规则

累计申报必须减前期已审金额，变更按审批生效版本覆盖；负进度需关联冲回证据。

钢筋领料不等于净工程量。M8把领料批次裁决为本期唯一可签认净量：净量上限=图纸净量+已批且当期生效变更；净料按上限池（图纸池优先、变更池其次）计入，超出部分隔离；损耗、错发强制隔离不进工程款；已安装但净量依据待补的批次结转下期并保留来源行；同批次重试按业务键拦截，不重复累计；非本期、未知清单项/性质同样隔离。发布失败整体回滚恢复旧版，重新归集按输入摘要生成新批次且来源行全部可追溯。

## 钢筋接口

`POST /api/rebar/runs` 接收 sample 或 csv（参数 `parameters` 可覆盖图纸净量、前审净量、已批变更量与变更目录），幂等保存；`GET /api/rebar/runs` 返回钢筋域历史；`POST /api/rebar/runs/<id>/review` 复核；`POST /api/rebar/runs/<id>/publish` 发布，`simulate_failure:true` 演练失败回滚；`POST /api/rebar/upload` 接收 multipart 文件；`GET /api/runs/<id>/archive` 导出含 accepted/quarantine/carry_forward 三类证据的CSV。

## 演示

1. 打开首页，核对当次计算、差异和隔离原因。
2. 切换模块查看源行及裁决依据。
3. 重跑相同样例，批次号与行数保持一致。
4. 复核后导出一份证据CSV。版本已变化的复核提交返回409。

## 输入与输出

输入列见 `docs/DATA-DICTIONARY.md`。项目包含dirty.csv、clean.csv、legacy.csv，统一走实际导入路径。钢筋领料样例为rebar.csv，列见数据字典REBAR_COLUMNS，经独立M8流水线处理。上传限制4MB，拒绝不带时区的时间。业务键按字符串保留，Decimal参与计算，空值不会当零。

`POST /api/runs` 接收sample或csv；`GET /api/runs`返回历史批次；`POST /api/runs/<id>/review`需要version与decision；`GET /api/runs/<id>/archive`返回唯一证据导出。

## 范围

样例均为虚构。单机复核工具不连接生产系统；不提供登录、远端数据库或自动支付。内存计算按4MB输入上限控制，SQLite事务保证结果完整写入。

## 目录

app为服务与规则，sample_data为输入，tests为测试，docs为定义与深度登记。
