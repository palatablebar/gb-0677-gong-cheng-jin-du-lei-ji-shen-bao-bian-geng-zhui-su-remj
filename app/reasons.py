REASONS={"BAD_COLUMNS":"列数不匹配","EMPTY_VALUE":"必填值为空","INVALID_NUMBER":"数字格式错误","INVALID_TIME":"时间缺少偏移或格式错误","DUPLICATE_CONFLICT":"同键取值冲突","UNKNOWN_REFERENCE":"引用不存在","STALE_VERSION":"版本已更新","EMPTY_FILE":"文件为空","HEADER_ONLY":"仅有表头","BLANK_ONLY":"全部为空行","BAD_PERIOD":"周期非法","OVER_CAP_NET":"领料超出图纸净量与已批变更上限","PENDING_EVIDENCE":"已安装未补齐净量依据，结转下期","REBAR_WASTE":"损耗隔离，不得进入正式工程量","REBAR_MISDELIVERY":"错发隔离，不得进入正式工程量","UNKNOWN_ITEM":"清单项未登记","UNKNOWN_NATURE":"领料性质未登记","BAD_QTY":"领料量非法","DUPLICATE_BATCH":"同批次重复提交，禁止重复累计","CHANGE_NOT_EFFECTIVE":"变更未生效或未批准"}
def reject(row, code, detail):
    return {**row,"reason":code,"detail":detail}
def sources(row):
    return row.get("_sources", [row.get("_line",0)])
