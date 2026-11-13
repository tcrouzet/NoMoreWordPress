# python3 server.py &
import http.server
import socketserver
import threading


def run_server():
    PORT = 8000
    while True:
        try:
            with socketserver.TCPServer(("", PORT), NoCacheHandler) as httpd:
                print(f"Serving at http://localhost:{PORT}")
                httpd.serve_forever()
        except OSError as e:
            print(f"Port {PORT} is already in use. Trying next port...")
            PORT += 1
            continue
        break

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=".", **kwargs)


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=".", **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()


thread = threading.Thread(target=run_server)
thread.daemon = True
thread.start()

input("Press Enter to exit...\n")
