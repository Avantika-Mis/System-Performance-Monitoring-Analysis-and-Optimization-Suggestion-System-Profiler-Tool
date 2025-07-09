import http.server
import socketserver
import json

class MetricsRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, metric_manager, *args, **kwargs):
        self.metric_manager = metric_manager
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.metric_manager.collect_metrics()
            response = json.dumps(self.metric_manager.metrics)
            self.wfile.write(response.encode())
        else:
            super().do_GET()

def start_http_server(metric_manager, port=8000):
    handler = lambda *args, **kwargs: MetricsRequestHandler(metric_manager, *args, **kwargs)
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving metrics at http://localhost:{port}")
        httpd.serve_forever()
