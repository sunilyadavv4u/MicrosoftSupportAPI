import csv, json, sqlite3
from pathlib import Path
from .config import settings

ROOT = Path(__file__).resolve().parents[1]

def load_manifest():
    path = (ROOT / settings.sources_manifest).resolve()
    return json.loads(path.read_text(encoding="utf-8"))

def connect():
    db = (ROOT / settings.database_path).resolve()
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db, timeout=60)
    con.row_factory = sqlite3.Row
    return con

def initialize_from_csv(reload=False):
    manifest = load_manifest()
    con = connect()
    counts = {}
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        for item in manifest["tables"]:
            table = item["table"]
            csv_path = ROOT / item["file"]
            if not csv_path.exists():
                raise FileNotFoundError(f"CSV not found: {csv_path}")
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if exists and not reload:
                counts[table] = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                continue
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                columns = reader.fieldnames or []
                if not columns:
                    raise ValueError(f"Missing CSV header: {csv_path}")
                con.execute(f'DROP TABLE IF EXISTS "{table}"')
                con.execute("CREATE TABLE " + '"' + table + '" (' +
                            ", ".join('"' + c.replace('"','""') + '" TEXT' for c in columns) + ")")
                marks = ",".join(["?"] * len(columns))
                col_sql = ",".join('"' + c.replace('"','""') + '"' for c in columns)
                insert = f'INSERT INTO "{table}" ({col_sql}) VALUES ({marks})'
                batch, count = [], 0
                for row in reader:
                    batch.append([row.get(c) for c in columns])
                    if len(batch) >= 5000:
                        con.executemany(insert, batch)
                        count += len(batch)
                        batch.clear()
                if batch:
                    con.executemany(insert, batch)
                    count += len(batch)
                counts[table] = count
        con.execute("""CREATE TABLE IF NOT EXISTS ApiWriteTest(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS ApiWriteTestAudit(
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            write_id INTEGER,
            operation TEXT NOT NULL,
            payload_json TEXT,
            created_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )""")
        con.commit()
        return counts
    finally:
        con.close()

def get_resource_info(resource):
    for item in load_manifest()["tables"]:
        if item["resource"] == resource:
            return item
    return None

def query_resource(resource, limit, offset, filters=None, date_from=None, date_to=None, modified_since=None, order_by=None):
    info = get_resource_info(resource)
    if not info:
        raise KeyError(resource)
    table = info["table"]
    con = connect()
    try:
        columns = [r["name"] for r in con.execute(f'PRAGMA table_info("{table}")').fetchall()]
        clauses, params = [], []
        for key, value in (filters or {}).items():
            if key in columns and value is not None:
                clauses.append(f'"{key}" = ?')
                params.append(str(value))
        date_column = None
        for candidate in ["WorkDate","WeekStartDate","PublishedDate","FeedbackDate","ViewedTimestamp","ViewTimestamp","ApprovalTimestamp","LastModifiedTimestamp","EffectiveFrom"]:
            if candidate in columns:
                date_column = candidate
                break
        if date_from:
            if not date_column: raise ValueError("This resource has no supported date column")
            clauses.append(f'"{date_column}" >= ?'); params.append(date_from)
        if date_to:
            if not date_column: raise ValueError("This resource has no supported date column")
            clauses.append(f'"{date_column}" <= ?'); params.append(date_to)
        if modified_since:
            if "LastModifiedTimestamp" not in columns:
                raise ValueError("modified_since is supported only on resources with LastModifiedTimestamp")
            clauses.append('"LastModifiedTimestamp" >= ?'); params.append(modified_since)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        total = con.execute(f'SELECT COUNT(*) FROM "{table}"{where}', params).fetchone()[0]
        safe_order = order_by if order_by in columns else None
        order = f' ORDER BY "{safe_order}"' if safe_order else " ORDER BY rowid"
        rows = con.execute(f'SELECT * FROM "{table}"{where}{order} LIMIT ? OFFSET ?', params+[limit,offset]).fetchall()
        return total, [dict(r) for r in rows], columns
    finally:
        con.close()

def write_test(resource,payload):
    con=connect()
    try:
        cur=con.execute("INSERT INTO ApiWriteTest(resource,payload_json) VALUES(?,?)",(resource,json.dumps(payload,ensure_ascii=False)))
        wid=cur.lastrowid
        con.execute("INSERT INTO ApiWriteTestAudit(write_id,operation,payload_json) VALUES(?,?,?)",(wid,"POST",json.dumps(payload,ensure_ascii=False)))
        con.commit()
        return wid
    finally: con.close()

def get_write(wid):
    con=connect()
    try:
        r=con.execute("SELECT * FROM ApiWriteTest WHERE id=?",(wid,)).fetchone()
        return dict(r) if r else None
    finally: con.close()

def update_write(wid,payload,replace=False):
    con=connect()
    try:
        r=con.execute("SELECT * FROM ApiWriteTest WHERE id=?",(wid,)).fetchone()
        if not r: return None
        old=json.loads(r["payload_json"])
        new=payload if replace else {**old,**payload}
        con.execute("UPDATE ApiWriteTest SET payload_json=? WHERE id=?",(json.dumps(new,ensure_ascii=False),wid))
        con.execute("INSERT INTO ApiWriteTestAudit(write_id,operation,payload_json) VALUES(?,?,?)",(wid,"PUT" if replace else "PATCH",json.dumps(new,ensure_ascii=False)))
        con.commit()
        return get_write(wid)
    finally: con.close()

def delete_write(wid):
    con=connect()
    try:
        r=con.execute("SELECT * FROM ApiWriteTest WHERE id=?",(wid,)).fetchone()
        if not r: return False
        con.execute("INSERT INTO ApiWriteTestAudit(write_id,operation,payload_json) VALUES(?,?,?)",(wid,"DELETE",r["payload_json"]))
        con.execute("DELETE FROM ApiWriteTest WHERE id=?",(wid,))
        con.commit()
        return True
    finally: con.close()
