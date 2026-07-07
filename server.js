import { createServer } from "node:http";
import { readFileSync, existsSync } from "node:fs";
import { extname, join } from "node:path";

const port = process.env.PORT || 3000;
const types = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json" };

createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");
  if (url.pathname === "/health") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: true, app: "Notes App" }));
    return;
  }
  const file = url.pathname === "/" ? "index.html" : url.pathname.slice(1);
  const path = join(process.cwd(), "public", file);
  if (!existsSync(path)) {
    res.writeHead(404);
    res.end("not found");
    return;
  }
  res.writeHead(200, { "content-type": types[extname(path)] || "text/plain" });
  res.end(readFileSync(path));
}).listen(port, () => console.log("Notes App" + " on :" + port));
