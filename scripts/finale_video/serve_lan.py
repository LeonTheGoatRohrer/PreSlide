"""Serve the finale film in the home network with seeking support (HTTP Range) for phones and smart TVs.

Usage: python scripts/finale_video/serve_lan.py [--port 8765] [--file Talwacht_Finale_Prototyp_v3.mp4]
Stop with Ctrl-C. Only the page and this one video are reachable.
"""
import argparse
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'deliverables/finale_video'
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8765)
parser.add_argument('--file', default='Talwacht_Finale_Prototyp_v3.mp4')
args = parser.parse_args()
VIDEO = OUT / args.file
PAGE = b"""<!doctype html><html lang="de"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Talwacht Finale</title>
<style>html,body{margin:0;height:100%;background:#000}video{display:block;width:100%;height:100%;object-fit:contain}</style>
<video src="/film.mp4" controls playsinline preload="metadata"></video></html>"""
CHUNK = 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def _send_page(self, head_only: bool) -> None:
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(PAGE)))
        self.end_headers()
        if not head_only:
            self.wfile.write(PAGE)

    def _send_video(self, head_only: bool) -> None:
        size = VIDEO.stat().st_size
        start, end, status = 0, size - 1, 200
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', self.headers.get('Range', ''))
        if match and (match[1] or match[2]):
            if match[1]:
                start = int(match[1])
                end = min(int(match[2]), size - 1) if match[2] else size - 1
            else:
                start = max(0, size - int(match[2]))
            if start > end:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.end_headers()
                return
            status = 206
        self.send_response(status)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        if status == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if head_only:
            return
        with VIDEO.open('rb') as handle:
            handle.seek(start)
            left = end - start + 1
            while left > 0:
                data = handle.read(min(CHUNK, left))
                if not data:
                    break
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionError):
                    return  # players routinely drop connections while seeking
                left -= len(data)

    def _route(self, head_only: bool) -> None:
        path = self.path.split('?')[0]
        if path == '/':
            self._send_page(head_only)
        elif path == '/film.mp4':
            self._send_video(head_only)
        else:
            self.send_error(404)

    def do_GET(self) -> None:
        self._route(False)

    def do_HEAD(self) -> None:
        self._route(True)


print(f'Talwacht-Film auf Port {args.port} (Strg+C beendet)', flush=True)
ThreadingHTTPServer(('0.0.0.0', args.port), Handler).serve_forever()
