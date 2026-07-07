from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json, mimetypes, random, sqlite3, time

APP_NAME = "Notes App"
SLUG = "notes-stash"
ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "app.db"

def db():
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""create table if not exists items (
        id integer primary key autoincrement,
        title text not null default '',
        body text not null default '',
        status text not null default '',
        meta text not null default '{}',
        created_at integer not null,
        updated_at integer not null
    )""")
    return con

def row_to_dict(row):
    item = dict(row)
    item["meta"] = json.loads(item["meta"] or "{}")
    return item

class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        size = int(self.headers.get("content-length", "0"))
        return json.loads(self.rfile.read(size) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.send_json({"ok": True, "app": APP_NAME})
        if path == "/api/items":
            with db() as con:
                rows = con.execute("select * from items order by updated_at desc, id desc").fetchall()
            return self.send_json([row_to_dict(r) for r in rows])
        if path == "/api/random":
            with db() as con:
                rows = con.execute("select * from items where status != 'hidden' order by random() limit 1").fetchall()
            return self.send_json(row_to_dict(rows[0]) if rows else {})
        if path.startswith("/s/"):
            code = path.split("/", 2)[2]
            with db() as con:
                row = con.execute("select * from items where title = ? limit 1", (code,)).fetchone()
                if row:
                    meta = json.loads(row["meta"] or "{}")
                    url = meta.get("url", "")
                    con.execute("update items set meta=?, updated_at=? where id=?", (json.dumps({**meta, "clicks": int(meta.get("clicks", 0)) + 1}), int(time.time()), row["id"]))
                    if url:
                        self.send_response(302)
                        self.send_header("location", url)
                        self.end_headers()
                        return
            self.send_error(404)
            return
        file_path = ROOT / "public" / ("index.html" if path == "/" else path.lstrip("/"))
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("content-type", mimetypes.guess_type(file_path)[0] or "text/plain")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if urlparse(self.path).path != "/api/items":
            self.send_error(404); return
        payload = self.read_json()
        now = int(time.time())
        with db() as con:
            cur = con.execute("insert into items(title, body, status, meta, created_at, updated_at) values(?,?,?,?,?,?)", (
                payload.get("title", ""), payload.get("body", ""), payload.get("status", ""), json.dumps(payload.get("meta", {})), now, now
            ))
            row = con.execute("select * from items where id=?", (cur.lastrowid,)).fetchone()
        self.send_json(row_to_dict(row), 201)

    def do_PUT(self):
        parts = urlparse(self.path).path.split("/")
        if len(parts) != 4 or parts[:3] != ["", "api", "items"]:
            self.send_error(404); return
        payload = self.read_json()
        now = int(time.time())
        with db() as con:
            con.execute("update items set title=?, body=?, status=?, meta=?, updated_at=? where id=?", (
                payload.get("title", ""), payload.get("body", ""), payload.get("status", ""), json.dumps(payload.get("meta", {})), now, int(parts[3])
            ))
            row = con.execute("select * from items where id=?", (int(parts[3]),)).fetchone()
        self.send_json(row_to_dict(row) if row else {})

    def do_DELETE(self):
        parts = urlparse(self.path).path.split("/")
        if len(parts) != 4 or parts[:3] != ["", "api", "items"]:
            self.send_error(404); return
        with db() as con:
            con.execute("delete from items where id=?", (int(parts[3]),))
        self.send_json({"ok": True})

print(f"{APP_NAME} on :{__import__('os').environ.get('PORT','3000')}")
ThreadingHTTPServer(("0.0.0.0", int(__import__("os").environ.get("PORT", "3000"))), Handler).serve_forever()
