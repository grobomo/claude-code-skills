#!/usr/bin/env python3
"""Minimal folder server for diff viewer. Run: python server.py [project_root]"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import urllib.parse
import secrets
import sys
import subprocess

# Security settings
ALLOWED_EXTENSIONS = {'.json', '.md', '.py', '.txt', '.yaml', '.yml', '.js', '.ts', '.html', '.css', '.sh', '.cfg', '.ini', '.toml'}
PROJECT_ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
AUTH_TOKEN = secrets.token_urlsafe(16)

def is_safe_path(path):
    """Check if path is under project root"""
    try:
        real_path = os.path.realpath(path)
        real_root = os.path.realpath(PROJECT_ROOT)
        return real_path.startswith(real_root)
    except:
        return False

def is_allowed_extension(path):
    """Check if file extension is allowed for writing"""
    ext = os.path.splitext(path)[1].lower()
    return ext in ALLOWED_EXTENSIONS

class FolderHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def check_token(self):
        """Verify auth token from header or query string"""
        token = self.headers.get('X-Auth-Token', '')
        if not token:
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            token = params.get('token', [''])[0]
        return token == AUTH_TOKEN

    def do_POST(self):
        # Save file endpoint
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
            file_path = data.get('path', '')
            content = data.get('content', '')
            token = data.get('token', '')

            # Security checks
            if token != AUTH_TOKEN:
                self.send_response(403)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Invalid token'}).encode())
                return

            if not file_path:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'No path provided'}).encode())
                return

            if not is_safe_path(file_path):
                self.send_response(403)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Path outside project root'}).encode())
                return

            if not is_allowed_extension(file_path):
                self.send_response(403)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'File type not allowed'}).encode())
                return

            # Create backup before saving
            if os.path.exists(file_path):
                import shutil
                from datetime import datetime
                backup_name = file_path + '.backup.' + datetime.now().strftime('%Y%m%d_%H%M%S')
                shutil.copy2(file_path, backup_name)

            # Save the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'path': file_path}).encode())
            print(f"[DiffServer] Saved: {file_path}")

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_GET(self):
        # Parse path from query string
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        folder_path = params.get('path', [''])[0]
        token = params.get('token', [''])[0]

        # Token check
        if token != AUTH_TOKEN:
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid token'}).encode())
            return

        # Path safety check
        if folder_path and not is_safe_path(folder_path):
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Path outside project root'}).encode())
            return

        # CORS headers for local file:// access
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        # Handle file read request
        file_path = params.get('file', [''])[0]
        if file_path:
            if not is_safe_path(file_path):
                self.wfile.write(json.dumps({'error': 'Path outside project root'}).encode())
                return
            if not os.path.isfile(file_path):
                self.wfile.write(json.dumps({'error': 'File not found'}).encode())
                return
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()

                # Get relative path from project root
                rel_path = os.path.relpath(file_path, PROJECT_ROOT).replace('\\', '/')

                # Try to get git HEAD version
                git_content = ''
                try:
                    result = subprocess.run(
                        ['git', 'show', f'HEAD:{rel_path}'],
                        capture_output=True, text=True, encoding='utf-8',
                        cwd=PROJECT_ROOT
                    )
                    if result.returncode == 0:
                        git_content = result.stdout
                except:
                    pass

                # Get git commits for this file
                commits = []
                git_status = 'ok'
                current_branch = ''
                try:
                    # Get branch
                    branch_result = subprocess.run(['git', 'branch', '--show-current'],
                        capture_output=True, text=True, encoding='utf-8', cwd=PROJECT_ROOT)
                    current_branch = branch_result.stdout.strip()

                    # Get commit history for file
                    log_result = subprocess.run(
                        ['git', 'log', '--format=%h|%s|%ar', '-5', '--follow', '--', rel_path],
                        capture_output=True, text=True, encoding='utf-8', cwd=PROJECT_ROOT)

                    for line in log_result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split('|', 2)
                            commit_id = parts[0]
                            # Get file content at this commit
                            try:
                                file_result = subprocess.run(
                                    ['git', 'show', f'{commit_id}:{rel_path}'],
                                    capture_output=True, text=True, encoding='utf-8', cwd=PROJECT_ROOT)
                                commit_content = file_result.stdout.split('\n') if file_result.returncode == 0 else []
                            except:
                                commit_content = []
                            commits.append({
                                'id': commit_id,
                                'msg': parts[1] if len(parts) > 1 else '',
                                'date': parts[2] if len(parts) > 2 else '',
                                'content': commit_content
                            })

                    if not commits:
                        # Check if file is ignored
                        ignore_check = subprocess.run(['git', 'check-ignore', '-q', rel_path],
                            capture_output=True, cwd=PROJECT_ROOT)
                        if ignore_check.returncode == 0:
                            git_status = 'ignored'
                        else:
                            tracked_check = subprocess.run(['git', 'ls-files', rel_path],
                                capture_output=True, text=True, encoding='utf-8', cwd=PROJECT_ROOT)
                            if not tracked_check.stdout.strip():
                                git_status = 'untracked'
                            else:
                                git_status = 'no_history'
                except Exception as e:
                    git_status = 'error'

                self.wfile.write(json.dumps({
                    'content': content,
                    'git_content': git_content,
                    'path': file_path,
                    'commits': commits,
                    'branch': current_branch,
                    'git_status': git_status
                }).encode())
                print(f"[DiffServer] Read: {file_path}")
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        if not folder_path or not os.path.isdir(folder_path):
            self.wfile.write(json.dumps({'error': 'Invalid path'}).encode())
            return

        # Build folder tree (2 levels deep)
        def get_tree(path, depth=0, max_depth=2):
            items = []
            try:
                for entry in sorted(os.listdir(path)):
                    if entry.startswith('.') and entry not in ['.mcp.json', '.env']:
                        continue
                    full_path = os.path.join(path, entry)
                    if os.path.isdir(full_path):
                        items.append({
                            'name': entry,
                            'type': 'dir',
                            'path': full_path,
                            'children': get_tree(full_path, depth + 1, max_depth) if depth < max_depth else []
                        })
                    else:
                        items.append({
                            'name': entry,
                            'type': 'file',
                            'path': full_path
                        })
            except PermissionError:
                pass
            return items

        tree = get_tree(folder_path)
        self.wfile.write(json.dumps({'path': folder_path, 'tree': tree}).encode())

    def log_message(self, format, *args):
        print(f"[DiffServer] {args[0]}")

if __name__ == '__main__':
    port = 8765

    # Write token to file for generate.py to read
    token_file = os.path.join(os.path.dirname(__file__), '.server_token')
    with open(token_file, 'w') as f:
        f.write(AUTH_TOKEN)

    server = HTTPServer(('localhost', port), FolderHandler)
    print(f"Diff folder server running on http://localhost:{port}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Auth token: {AUTH_TOKEN}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        # Clean up token file
        if os.path.exists(token_file):
            os.remove(token_file)
        print("\nServer stopped")
