from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote, unquote
import html, json, mimetypes, os, re, secrets, sqlite3, string, time, urllib.request

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

def get_json(url):
    req = urllib.request.Request(url, headers={"user-agent": "UtapusAgent-demo/0.2"})
    with urllib.request.urlopen(req, timeout=8) as res:
        return json.loads(res.read().decode("utf-8"))

def get_text(url):
    req = urllib.request.Request(url, headers={"user-agent": "UtapusAgent-demo/0.2"})
    with urllib.request.urlopen(req, timeout=8) as res:
        return res.read(200000).decode("utf-8", "ignore")

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
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        if path == "/health":
            return self.send_json({"ok": True, "app": APP_NAME})
        if path == "/api/items":
            with db() as con:
                rows = con.execute("select * from items order by updated_at desc, id desc").fetchall()
            return self.send_json([row_to_dict(r) for r in rows])
        if path == "/api/weather":
            city = qs.get("city", [""])[0].strip()
            units = qs.get("units", ["C"])[0]
            if not city:
                return self.send_json({"error": "city is required"}, 400)
            geo = get_json("https://geocoding-api.open-meteo.com/v1/search?name=" + quote(city) + "&count=1&language=en&format=json")
            place = (geo.get("results") or [None])[0]
            if not place:
                return self.send_json({"error": "city not found"}, 404)
            unit_arg = "&temperature_unit=fahrenheit" if units == "F" else ""
            forecast = get_json("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto%s" % (place["latitude"], place["longitude"], unit_arg))
            return self.send_json({"place": place, "forecast": forecast})
        if path == "/api/external-quote":
            data = get_json("https://dummyjson.com/quotes/random")
            return self.send_json({"quote": data.get("quote", ""), "author": data.get("author", "Unknown")})
        if path == "/api/meal":
            q = qs.get("q", [""])[0].strip()
            if not q:
                return self.send_json({"error": "q is required"}, 400)
            data = get_json("https://www.themealdb.com/api/json/v1/1/search.php?s=" + quote(q))
            meal = (data.get("meals") or [None])[0]
            if not meal:
                return self.send_json({"error": "recipe not found"}, 404)
            ingredients = []
            for i in range(1, 21):
                ing = (meal.get(f"strIngredient{i}") or "").strip()
                measure = (meal.get(f"strMeasure{i}") or "").strip()
                if ing:
                    ingredients.append((measure + " " + ing).strip())
            return self.send_json({"title": meal.get("strMeal", ""), "ingredients": "\n".join(ingredients), "steps": meal.get("strInstructions", ""), "source": meal.get("strSource") or meal.get("strYoutube") or ""})
        if path == "/api/page-title":
            url = qs.get("url", [""])[0].strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                return self.send_json({"error": "http or https URL is required"}, 400)
            text = get_text(url)
            match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
            title = html.unescape(re.sub(r"\s+", " ", match.group(1)).strip()) if match else url
            return self.send_json({"title": title})
        if path == "/api/password":
            length = max(8, min(128, int(qs.get("length", ["20"])[0] or 20)))
            symbols = qs.get("symbols", ["true"])[0] != "false"
            alphabet = string.ascii_letters + string.digits + ("!@#$%^&*()-_=+[]{};:,.?/" if symbols else "")
            return self.send_json({"password": "".join(secrets.choice(alphabet) for _ in range(length))})
        if path == "/api/random":
            with db() as con:
                rows = con.execute("select * from items where status != 'hidden' order by random() limit 1").fetchall()
            return self.send_json(row_to_dict(rows[0]) if rows else {})
        if path.startswith("/post/"):
            slug = unquote(path.split("/", 2)[2])
            with db() as con:
                row = con.execute("select * from items where json_extract(meta, '$.slug') = ? or title = ? limit 1", (slug, slug)).fetchone()
            if not row:
                self.send_error(404); return
            item = row_to_dict(row)
            data = ("<!doctype html><title>%s</title><main><h1>%s</h1><article>%s</article></main>" % (html.escape(item["title"]), html.escape(item["title"]), html.escape(item["body"]).replace("\n", "<br>"))).encode()
            self.send_response(200); self.send_header("content-type", "text/html"); self.send_header("content-length", str(len(data))); self.end_headers(); self.wfile.write(data); return
        if path.startswith("/s/"):
            code = path.split("/", 2)[2]
            with db() as con:
                row = con.execute("select * from items where title = ? limit 1", (code,)).fetchone()
                if row:
                    meta = json.loads(row["meta"] or "{}")
                    url = meta.get("url", "")
                    con.execute("update items set meta=?, updated_at=? where id=?", (json.dumps({**meta, "clicks": int(meta.get("clicks", 0)) + 1}), int(time.time()), row["id"]))
                    if url:
                        self.send_response(302); self.send_header("location", url); self.end_headers(); return
            self.send_error(404); return
        file_path = ROOT / "public" / ("index.html" if path == "/" else path.lstrip("/"))
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404); return
        data = file_path.read_bytes()
        self.send_response(200); self.send_header("content-type", mimetypes.guess_type(file_path)[0] or "text/plain"); self.send_header("content-length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_POST(self):
        if urlparse(self.path).path != "/api/items":
            self.send_error(404); return
        payload = self.read_json(); now = int(time.time())
        with db() as con:
            cur = con.execute("insert into items(title, body, status, meta, created_at, updated_at) values(?,?,?,?,?,?)", (payload.get("title", ""), payload.get("body", ""), payload.get("status", ""), json.dumps(payload.get("meta", {})), now, now))
            row = con.execute("select * from items where id=?", (cur.lastrowid,)).fetchone()
        self.send_json(row_to_dict(row), 201)

    def do_PUT(self):
        parts = urlparse(self.path).path.split("/")
        if len(parts) != 4 or parts[:3] != ["", "api", "items"]:
            self.send_error(404); return
        payload = self.read_json(); now = int(time.time())
        with db() as con:
            con.execute("update items set title=?, body=?, status=?, meta=?, updated_at=? where id=?", (payload.get("title", ""), payload.get("body", ""), payload.get("status", ""), json.dumps(payload.get("meta", {})), now, int(parts[3])))
            row = con.execute("select * from items where id=?", (int(parts[3]),)).fetchone()
        self.send_json(row_to_dict(row) if row else {})

    def do_DELETE(self):
        parts = urlparse(self.path).path.split("/")
        if len(parts) != 4 or parts[:3] != ["", "api", "items"]:
            self.send_error(404); return
        with db() as con:
            con.execute("delete from items where id=?", (int(parts[3]),))
        self.send_json({"ok": True})

print(f"{APP_NAME} on :{os.environ.get('PORT','3000')}")
ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "3000"))), Handler).serve_forever()
