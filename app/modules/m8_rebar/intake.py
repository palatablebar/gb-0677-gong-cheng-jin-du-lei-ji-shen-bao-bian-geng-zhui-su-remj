import csv,io
from app.config import REBAR_COLUMNS
from app.errors import DomainError
def decode(raw):
    for encoding in ("utf-8-sig","gb18030"):
        try:return raw.decode(encoding),encoding
        except UnicodeDecodeError:continue
    raise DomainError("ENCODING","无法识别文件编码")
def evaluate(raw,context=None):
    text,encoding=decode(raw)
    if not text:raise DomainError("EMPTY_FILE","文件为空")
    if not text.strip():raise DomainError("BLANK_ONLY","全部为空行")
    stream=csv.reader(io.StringIO(text,newline=""))
    header=next(stream,None)
    if header!=REBAR_COLUMNS:raise DomainError("BAD_HEADER","表头不匹配")
    rows=[];bad=[];seen={};duplicate=blank=repeated=count=0
    try:
        for cells in stream:
            count+=1;line=stream.line_num
            if not cells or not any(c.strip() for c in cells):blank+=1;continue
            if cells==header:repeated+=1;continue
            row={"_line":line,"_sources":[line],"_raw":cells}
            if len(cells)!=len(header):
                from app.reasons import reject
                bad.append(reject(row,"BAD_COLUMNS","列数不匹配"));continue
            row.update(dict(zip(REBAR_COLUMNS,[x.strip() for x in cells])))
            key=row["batch_no"]
            if not key:
                from app.reasons import reject
                bad.append(reject(row,"EMPTY_VALUE","批次号为空"));continue
            if key in seen:
                from app.reasons import reject
                previous=seen[key]
                if cells==previous["_raw"]:
                    duplicate+=1
                    bad.append(reject({**row,"_retry_of":line},"DUPLICATE_BATCH","同批次完全重复提交，不重复累计"))
                else:
                    bad.append(reject(row,"DUPLICATE_CONFLICT","同批次不同值，隔离待核"))
                continue
            seen[key]=row;rows.append(row)
    except csv.Error:raise DomainError("BAD_CSV","引号未闭合或文件损坏")
    if count==0:raise DomainError("HEADER_ONLY","仅有表头")
    if not rows and not bad:raise DomainError("BLANK_ONLY","全部为空行")
    return {"rows":rows,"quarantine":bad,"metrics":{"input":count,"accepted":len(rows),"quarantine":len(bad),"duplicate":duplicate,"blank":blank,"repeated_headers":repeated,"encoding":encoding}}
