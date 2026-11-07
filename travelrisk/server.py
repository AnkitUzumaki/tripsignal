"""HTTP application entry point and API routes."""
import json, logging, mimetypes, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from .config import AIRPORTS, ROOT, STATIC_DIR, SETTINGS
from .service import assess

logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO"),format="%(asctime)s %(levelname)s %(message)s")
LOG=logging.getLogger("tripsignal")

class Handler(BaseHTTPRequestHandler):
    server_version="TripSignal/0.2"
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/health": return self.json_response({"status":"ok"})
        if path=="/api/airports": return self.json_response(AIRPORTS)
        if path=="/": return self.static_file("index.html")
        if path == "/app.js":
            asset = "app.js" if (STATIC_DIR / "app.js").is_file() else "app.js.txt"
            return self.static_file(asset, "text/javascript")
        if path == "/styles.css": return self.static_file("styles.css")
        self.send_error(404)
    def do_POST(self):
        if urlparse(self.path).path!="/api/assess": self.send_error(404); return
        if "application/json" not in self.headers.get("Content-Type",""):
            self.json_response({"error":"Content-Type must be application/json."},415); return
        try: length=int(self.headers.get("Content-Length","0"))
        except ValueError: length=0
        if length<=0 or length>SETTINGS["maximum_request_bytes"]:
            self.json_response({"error":"Request body is empty or too large."},413); return
        try:
            payload=json.loads(self.rfile.read(length))
            if not isinstance(payload,dict): raise ValueError("Request body must be a JSON object.")
            result=assess(payload)
            self.json_response(result)
        except (ValueError,TypeError) as exc: self.json_response({"error":str(exc)},400)
        except Exception:
            LOG.exception("Assessment request failed")
            self.json_response({"error":"Assessment could not be completed. Check server logs and try again."},502)
    def static_file(self,name,content_type_override=None):
        path=(STATIC_DIR/name).resolve()
        if STATIC_DIR.resolve() not in path.parents or not path.is_file(): self.send_error(404); return
        body=path.read_bytes(); content_type=content_type_override or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200); self.send_header("Content-Type",content_type+"; charset=utf-8"); self.send_header("Content-Length",str(len(body)))
        self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Referrer-Policy","no-referrer")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers(); self.wfile.write(body)
    def json_response(self,obj,status=200):
        body=json.dumps(obj,ensure_ascii=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(body)
    def log_message(self,fmt,*args): LOG.info("%s %s",self.address_string(),fmt%args)

def main():
    host=os.getenv("HOST",SETTINGS["host"]); port=int(os.getenv("PORT",SETTINGS["port"]))
    server=ThreadingHTTPServer((host,port),Handler); server.daemon_threads=True
    LOG.info("TripSignal listening at http://%s:%s",host,port)
    try: server.serve_forever()
    except KeyboardInterrupt: LOG.info("Shutting down")
    finally: server.server_close()
