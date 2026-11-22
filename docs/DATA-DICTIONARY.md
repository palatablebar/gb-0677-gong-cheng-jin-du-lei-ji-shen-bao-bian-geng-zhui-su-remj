# 计量定义

claim_id唯一；item为清单编码，支持钢筋与001等别名。period为YYYY-MM。累计数量按t或m³保存，当前周期工程量=本次累计-前期已审累计。previous_revisions参数可指定更正后的前审数量，重新计算形成不同批次，不覆盖旧证据。

C0原始价100元，C1自2026-11生效为120元，DRAFT未批准不可结算。负进度必须reversal=approved作为已批冲回标记。扣留质保金5%、预付款扣回10%分别按分量化，净额=本期总额-质保金-预付款扣回，负进度同步冲回扣留。reported为原申报净额，差异=复算净额-reported。

业务ID和超大整数按文本保形；Decimal参与数量金额计算，对外序列化为字符串。哨兵集合定义在app/values.py，缺失值不能当零。所有时间带UTC偏移，先转UTC比较，业务日按指定地区划分。区间统一[start,end)。重复业务键保留第一条、完全相同行计重复；值冲突行隔离且保留原值。空文件、全空白、仅表头分开拒绝。

运行清单包括输入sha256、规则版本、参数、生成时刻与耗时。源行编号以CSV解析器的物理结束行号表示，引号内换行不增加记录数。输入超过4MB返回413，非法表头和类型返回422，失效版本复核返回409。

# 钢筋领料（M8）

输入列REBAR_COLUMNS：`batch_no,item,period,issue_qty,issue_nature,change_id,note`。batch_no为领料批次业务键，字符串保形，重复完全相同行计重试并隔离（DUPLICATE_BATCH，不重复累计），同键不同值隔离冲突（DUPLICATE_CONFLICT）。item仅认钢筋/001，映射001，单位t。period必须等于裁决周期parameters.period（默认2026-11），否则BAD_PERIOD退回重新归集。issue_qty为正数Decimal，空值按EMPTY_VALUE隔离不当零。issue_nature仅认净料/损耗/错发（兼容英文net/waste/misdelivery）。

裁决参数（REBAR_DEFAULT_PARAMS，可被parameters覆盖）：drawing_net_qty图纸净量（默认项001=95）、approved_change_qty已批变更量（默认C2=5）、previous_approved_net前期已审累计净量（默认75）、changes变更目录（approved+effective<=周期才生效；未批C3不进入上限，参数引用未生效变更返回CHANGE_NOT_EFFECTIVE隔离）。

裁决口径：净量上限cap=图纸净量+已批生效变更量；净料按图纸池优先、变更池其次顺序计入，admitted_qty为计入净量、excess_qty为超限隔离量（OVER_CAP_NET）；损耗REBAR_WASTE、错发REBAR_MISDELIVERY整批隔离不进工程款；note为“依据待补”的净料进carry_forward（PENDING_EVIDENCE），本期不签、来源保留、下期补齐重新归集。本期唯一可签净量current_period_net=累计已签净量-前期已审；为负则NEGATIVE_INCREMENT阻断。lineage_balanced保证物理行全部有去向，重新归集不丢来源记录。发布在publish_events登记，失败回滚不产生事件。