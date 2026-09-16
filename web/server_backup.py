from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen
import json


PORT = 8080
API = "https://api.coinbase.com/v2/prices/BTC-USD/spot"


class Handler(SimpleHTTPRequestHandler):

    def do_GET(self):

        if self.path == "/api/btc":

            try:
                with urlopen(API, timeout=10) as response:
                    data = json.loads(
                        response.read().decode("utf-8")
                    )

                price = float(data["data"]["amount"])

                result = {
                    "price": price
                }

                body = json.dumps(result).encode("utf-8")

                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    "application/json"
                )
                self.send_header(
                    "Access-Control-Allow-Origin",
                    "*"
                )
                self.send_header(
                    "Content-Length",
                    str(len(body))
                )
                self.end_headers()

                self.wfile.write(body)

            except Exception as e:

                body = json.dumps({
                    "error": str(e)
                }).encode("utf-8")

                self.send_response(500)
                self.send_header(
                    "Content-Type",
                    "application/json"
                )
                self.send_header(
                    "Content-Length",
                    str(len(body))
                )
                self.end_headers()

                self.wfile.write(body)

            return

        super().do_GET()


server = ThreadingHTTPServer(
    ("", PORT),
    Handler
)

print(
    f"BALOCHFX server running on http://127.0.0.1:{PORT}"
)

server.serve_forever()
