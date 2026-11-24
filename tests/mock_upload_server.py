"""Faux serveur « Apps Script » pour tester l'envoi des données sans Google.

Modes (attribut `mode`, modifiable pendant le test) :
  ok      -> 200 + {"ok": true}            avec en-tête CORS
  flaky   -> 500 les 2 premières fois, puis ok
  nocors  -> 200 SANS en-tête CORS (le navigateur ne peut pas lire la réponse)
  reject  -> 200 + {"ok": false, "error": "invalid:header"}
  down    -> coupe la connexion sans répondre (erreur réseau)
Toutes les requêtes reçues sont gardées dans `requests` (en-têtes + corps).
"""
import http.server
import json
import socketserver
import threading


class MockUpload:
    def __init__(self):
        self.mode = "ok"
        self.requests = []
        self.flaky_count = 0
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_OPTIONS(self):   # ne devrait jamais arriver (text/plain = pas de preflight)
                outer.requests.append({"method": "OPTIONS", "headers": dict(self.headers), "body": ""})
                self.send_response(204)
                self.end_headers()

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(n).decode("utf-8")
                outer.requests.append({"method": "POST", "mode": outer.mode, "headers": dict(self.headers), "body": body})
                m = outer.mode
                if m == "down":
                    self.close_connection = True
                    self.connection.shutdown(2)
                    return
                if m == "flaky" and outer.flaky_count < 2:
                    outer.flaky_count += 1
                    self.send_response(500)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    return
                answer = {"ok": False, "error": "invalid:header"} if m == "reject" else {"ok": True, "status": "stored"}
                data = json.dumps(answer).encode()
                self.send_response(200)
                if m != "nocors":
                    self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        socketserver.ThreadingTCPServer.allow_reuse_address = True
        socketserver.ThreadingTCPServer.daemon_threads = True
        self.httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/exec"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def shutdown(self):
        self.httpd.shutdown()
