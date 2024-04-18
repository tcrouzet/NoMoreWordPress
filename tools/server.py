# python3 server.py &
import http.server
import socketserver
import threading

PORT = 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=".", **kwargs)

def run_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()

thread = threading.Thread(target=run_server)
thread.daemon = True
thread.start()

input("Press Enter to exit...\n")
