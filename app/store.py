import sqlite3,json
from pathlib import Path
from app.config import DATA_DIR
from app.errors import DomainError
def connect():
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DATA_DIR/"records.db",timeout=20)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY,payload TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,decision TEXT NOT NULL DEFAULT '待复核',domain TEXT NOT NULL DEFAULT 'claim')")
    cols={row[1] for row in db.execute("PRAGMA table_info(runs)")}
    if "domain" not in cols:
        db.execute("ALTER TABLE runs ADD COLUMN domain TEXT NOT NULL DEFAULT 'claim'")
    db.execute("CREATE TABLE IF NOT EXISTS publish_events (id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL,version INTEGER NOT NULL,created_at TEXT NOT NULL DEFAULT (datetime('now')),FOREIGN KEY(run_id) REFERENCES runs(id))")
    return db
def save(run_id,payload,domain="claim"):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO runs(id,payload,domain) VALUES (?,?,?)",(run_id,json.dumps(payload,ensure_ascii=False),domain))
    return get(run_id)
def get(run_id):
    with connect() as db:row=db.execute("SELECT payload,version,decision,domain FROM runs WHERE id=?",(run_id,)).fetchone()
    if not row:raise DomainError("NOT_FOUND","批次不存在",404)
    return {**json.loads(row[0]),"version":row[1],"decision":row[2],"domain":row[3]}
def latest(domain=None):
    with connect() as db:
        if domain:
            row=db.execute("SELECT id FROM runs WHERE domain=? ORDER BY rowid DESC LIMIT 1",(domain,)).fetchone()
        else:
            row=db.execute("SELECT id FROM runs ORDER BY rowid DESC LIMIT 1").fetchone()
    return get(row[0]) if row else None
def history(domain=None):
    with connect() as db:
        if domain:
            rows=db.execute("SELECT id,version,decision FROM runs WHERE domain=? ORDER BY rowid DESC",(domain,)).fetchall()
        else:
            rows=db.execute("SELECT id,version,decision FROM runs ORDER BY rowid DESC").fetchall()
    return [{"run_id":i,"version":v,"decision":d} for i,v,d in rows]
def review(run_id,version,decision):
    if decision not in {"已复核","退回复核"}:raise DomainError("BAD_DECISION","复核状态无效")
    with connect() as db:
        cursor=db.execute("UPDATE runs SET version=version+1,decision=? WHERE id=? AND version=?",(decision,run_id,version))
        if cursor.rowcount!=1:
            if not db.execute("SELECT 1 FROM runs WHERE id=?",(run_id,)).fetchone():raise DomainError("NOT_FOUND","批次不存在",404)
            raise DomainError("STALE_VERSION","版本已更新，请刷新",409)
    return get(run_id)
def publish(run_id,version,fail=False):
    """发布本期签认；fail=True用于演练发布失败，事务整体回滚并恢复旧版。"""
    with connect() as db:
        row=db.execute("SELECT version,decision,payload FROM runs WHERE id=?",(run_id,)).fetchone()
        if not row:raise DomainError("NOT_FOUND","批次不存在",404)
        current_version=row[0]
        if current_version!=version:raise DomainError("STALE_VERSION","版本已更新，请刷新",409)
        if fail:raise DomainError("PUBLISH_FAILED","发布失败：已回滚，工作台恢复旧版",409)
        payload=json.loads(row[2])
        payload.setdefault("decision_detail",{})["published"]=True
        db.execute("UPDATE runs SET version=version+1,decision='已发布',payload=? WHERE id=?",(json.dumps(payload,ensure_ascii=False),run_id))
        db.execute("INSERT INTO publish_events(run_id,version) VALUES (?,?)",(run_id,current_version+1))
    return get(run_id)
def published_runs():
    with connect() as db:
        return [r[0] for r in db.execute("SELECT DISTINCT run_id FROM publish_events ORDER BY id")]
