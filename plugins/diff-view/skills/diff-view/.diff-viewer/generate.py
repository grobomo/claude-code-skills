import html
import os
import json
import sys
import subprocess

# Get args or use defaults
if len(sys.argv) >= 3:
    old_file = sys.argv[1]
    new_file = sys.argv[2]
else:
    old_file = "README.md"
    new_file = "README.md"

with open(old_file, 'r', encoding='utf-8') as f:
    old_content = f.read()
with open(new_file, 'r', encoding='utf-8') as f:
    new_content = f.read()

old_lines = old_content.split('\n')
new_lines = new_content.split('\n')

old_lines_js = json.dumps(old_lines)
new_lines_js = json.dumps(new_lines)

# Get git history for THIS specific file
try:
    result = subprocess.run(['git', 'log', '--format=%h|%s|%ar', '-5', '--follow', '--', new_file],
                           capture_output=True, text=True, encoding='utf-8')
    commits = []
    for line in result.stdout.strip().split('\n'):
        if line:
            parts = line.split('|', 2)
            commit_id = parts[0]
            # Get file content at this commit
            try:
                file_result = subprocess.run(['git', 'show', f'{commit_id}:{new_file}'],
                                            capture_output=True, text=True, encoding='utf-8')
                content = file_result.stdout if file_result.returncode == 0 else ''
            except:
                content = ''
            commits.append({
                'id': commit_id,
                'msg': parts[1] if len(parts) > 1 else '',
                'date': parts[2] if len(parts) > 2 else '',
                'content': content.split('\n') if content else []
            })
except:
    commits = []

# Get current branch and check git status
git_status = 'ok'
current_branch = ''
try:
    # Check if we're in a git repo
    repo_check = subprocess.run(['git', 'rev-parse', '--git-dir'], capture_output=True, text=True, encoding='utf-8')
    if repo_check.returncode != 0:
        git_status = 'no_repo'
    else:
        branch_result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, encoding='utf-8')
        current_branch = branch_result.stdout.strip()

        # Check if file is ignored
        if not commits:
            ignore_check = subprocess.run(['git', 'check-ignore', '-q', new_file], capture_output=True, text=True, encoding='utf-8')
            if ignore_check.returncode == 0:
                git_status = 'ignored'
            else:
                # Check if file is tracked
                tracked_check = subprocess.run(['git', 'ls-files', new_file], capture_output=True, text=True, encoding='utf-8')
                if not tracked_check.stdout.strip():
                    git_status = 'untracked'
                else:
                    git_status = 'no_history'
except:
    git_status = 'error'

commits_js = json.dumps(commits)
branch_js = json.dumps(current_branch)
git_status_js = json.dumps(git_status)

# Get folder structure for navigation
current_dir = os.path.dirname(os.path.abspath(new_file)) or os.getcwd()
def get_tree(path, depth=0, max_depth=3):
    if depth > max_depth:
        return []
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
    except:
        pass
    return items

# Build folder trees for current dir and parent dirs (3 levels for offline use)
folder_trees = {}
nav_dir = current_dir
for i in range(3):
    folder_trees[nav_dir] = get_tree(nav_dir, 0, 2)
    parent = os.path.dirname(nav_dir)
    if parent == nav_dir:  # reached root
        break
    nav_dir = parent

folder_trees_js = json.dumps(folder_trees)
current_dir_js = json.dumps(current_dir)
current_file_js = json.dumps(os.path.abspath(new_file))

# Read server token if available
server_token = ''
token_file = os.path.join(os.path.dirname(__file__), '.server_token')
if os.path.exists(token_file):
    with open(token_file, 'r') as f:
        server_token = f.read().strip()
server_token_js = json.dumps(server_token)

html_content = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Diff Viewer</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Consolas,monospace;font-size:16px;background:#1e1e1e;color:#d4d4d4;padding:10px}}
h1{{color:#dcdcaa;text-align:center;margin:10px 0}}
.file-header{{background:#0e639c;color:#fff;padding:8px 15px;font-weight:700;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:20}}
.buttons{{display:flex;gap:8px;align-items:center}}
.buttons button{{padding:6px 16px;border:1px solid #5a5a5a;border-radius:3px;cursor:pointer;font-size:14px}}
.save-btn{{background:#2d7d2d;color:#fff}}
.save-btn:hover{{background:#3a9a3a}}
.cancel-btn{{background:#3c3c3c;color:#d4d4d4}}
.cancel-btn:hover{{background:#4a4a4a}}
.status{{font-size:12px;color:#89d185}}
.main-wrapper{{display:flex;height:85vh}}
.git-panel{{width:200px;min-width:200px;background:#252526;overflow-y:auto;overflow-x:hidden;scrollbar-width:none;-ms-overflow-style:none;position:relative;transition:width 0.2s,min-width 0.2s}}
.git-panel::-webkit-scrollbar{{display:none}}
.git-panel.collapsed{{width:30px!important;min-width:30px!important;cursor:pointer}}
.git-panel.collapsed .git-panel-inner{{display:none}}
.git-resizer{{position:absolute;top:0;bottom:0;right:0;width:6px;background:#3c3c3c;cursor:ew-resize}}
.git-resizer:hover{{background:#0e639c}}
.git-toggle{{background:#333;color:#888;border:none;padding:5px;cursor:pointer;width:100%;text-align:center;font-size:12px}}
.git-toggle:hover{{color:#fff}}
.git-panel.collapsed .git-toggle{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:auto;padding:8px 10px}}
.git-header{{padding:8px;color:#dcdcaa;font-size:12px;font-weight:700;border-bottom:1px solid #3c3c3c}}
.branch-name{{padding:6px 8px;color:#4ec9b0;font-size:11px;background:#1a1a1a;border-bottom:1px solid #3c3c3c}}
.git-panel.collapsed .git-header,.git-panel.collapsed .commit-list,.git-panel.collapsed .branch-name,.git-panel.collapsed .git-resizer{{display:none}}
.commit-list{{padding:8px}}
.commit{{position:relative;padding-left:20px;margin-bottom:12px}}
.commit:before{{content:"";position:absolute;left:6px;top:0;bottom:-12px;width:2px;background:#444}}
.commit:last-child:before{{bottom:0}}
.commit:after{{content:"";position:absolute;left:2px;top:4px;width:10px;height:10px;border-radius:50%;background:#0e639c;border:2px solid #1e1e1e}}
.commit{{cursor:pointer}}
.commit:hover{{background:#333}}
.commit.selected:after{{background:#89d185}}
.commit-id{{color:#569cd6;font-size:11px}}
.commit-msg{{color:#9cdcfe;font-size:12px;margin-top:2px;word-wrap:break-word}}
.commit-date{{color:#666;font-size:10px;margin-top:1px}}
.git-status{{padding:8px;font-size:11px;color:#888;font-style:italic}}
.git-panel-inner{{display:flex;flex-direction:column;height:100%}}
.git-section{{flex:1;overflow-y:auto}}
.file-browser{{display:flex;flex-direction:column;border-top:3px solid #555;cursor:ns-resize}}
.file-browser-content{{flex:1;display:flex;flex-direction:column;min-height:150px}}
.browser-header{{display:flex;align-items:center;padding:4px 8px;background:#2d2d2d;gap:4px}}
.browser-path{{flex:1;font-size:10px;color:#888;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}}
.browser-path:hover{{color:#fff}}
.browser-path-input{{flex:1;font-size:10px;color:#d4d4d4;background:#1a1a1a;border:1px solid #0e639c;padding:2px 4px;outline:none;display:none}}
.browser-path-input.show{{display:block}}
.browser-path.hidden{{display:none}}
.browser-icons{{display:flex;gap:2px}}
.browser-btn{{background:none;border:none;color:#888;cursor:pointer;font-size:11px;padding:2px 4px;font-family:Segoe UI Symbol,sans-serif}}
.browser-btn:hover{{color:#fff;background:#444}}
.browser-header{{position:relative}}
.search-box{{display:none;position:absolute;right:0;top:100%;width:140px;background:#1a1a1a;border:1px solid #3c3c3c;border-radius:3px;z-index:30;padding:2px 4px;align-items:center}}
.search-box.show{{display:flex}}
.search-box input{{flex:1;background:transparent;border:none;color:#d4d4d4;padding:4px;font-size:11px;outline:none;min-width:0}}
.search-clear{{background:none;border:none;color:#666;cursor:pointer;font-size:12px;padding:0 2px;display:none}}
.search-clear.show{{display:block}}
.search-clear:hover{{color:#fff}}
.no-results{{display:none;color:#666;font-style:italic;text-align:center;padding:20px;font-size:11px}}
.no-results.show{{display:block}}
.file-tree{{flex:1;padding:4px 0;font-size:11px;overflow-y:auto;scrollbar-width:none;position:relative}}
.file-tree::-webkit-scrollbar{{display:none}}
.tree-item{{padding:2px 8px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tree-item:hover{{background:#333}}
.tree-item.current{{background:#3c3c3c;color:#89d185;font-weight:700;border-left:3px solid #89d185}}
.tree-dir{{color:#dcdcaa}}
.tree-file{{color:#9cdcfe;padding-left:12px}}
.tree-children{{padding-left:12px;display:none}}
.tree-children.open{{display:block}}
.tree-toggle{{color:#888;margin-right:4px}}
.diff-wrapper{{flex:1;position:relative;border:1px solid #3c3c3c}}
.diff-container{{height:100%;overflow:hidden;display:flex}}
.left-panel{{width:50%;overflow-y:auto;overflow-x:hidden;scrollbar-width:none;-ms-overflow-style:none}}
.left-panel::-webkit-scrollbar{{display:none}}
.right-panel{{flex:1;overflow:hidden;display:flex;flex-direction:column}}
.editor-wrapper{{flex:1;display:flex;overflow:hidden}}
.line-numbers{{min-width:40px;padding:2px 6px;text-align:right;color:#606060;background:#1a1a1a;border-right:1px solid #3c3c3c;font:inherit;line-height:22px;overflow:hidden;white-space:pre}}
.resizer{{position:absolute;top:0;bottom:0;width:12px;background:#555;cursor:ew-resize;z-index:10;left:50%;margin-left:-6px}}
.resizer:hover{{background:#0e639c}}
.panel-header{{background:#2d2d2d;padding:5px 10px;font-weight:700;text-align:center;position:sticky;top:0}}
.left-panel .panel-header{{color:#f48771}}
.right-panel .panel-header{{color:#89d185}}
.line-row{{display:flex;min-height:22px}}
.line-num{{min-width:40px;padding:2px 6px;text-align:right;color:#606060;background:#1a1a1a;border-right:1px solid #3c3c3c;flex-shrink:0;line-height:22px}}
.line-content{{flex:1;padding:2px 8px;white-space:pre-wrap;word-wrap:break-word;line-height:22px}}
.changed-left{{background:#3e2a2a}}
.added{{background:#2a3e2a}}
.removed{{background:#3e2a2a}}
.editor{{flex:1;background:#1e1e1e;color:#d4d4d4;border:none;padding:2px 8px;font:inherit;line-height:22px;resize:none;outline:none;overflow-y:auto;scrollbar-width:none;-ms-overflow-style:none;white-space:pre;overflow-wrap:normal}}
.editor::-webkit-scrollbar{{display:none}}
</style>
</head>
<body>
<h1>Diff Viewer</h1>
<div class="file-header">
<span id="fileName">{html.escape(new_file)}</span>
<div class="buttons">
<span class="status" id="status"></span>
<button class="save-btn" onclick="saveFile()">Save</button>
<button class="cancel-btn" onclick="window.close()">Cancel</button>
</div>
</div>
<div class="main-wrapper">
<div class="git-panel" id="gitPanel">
<button class="git-toggle" onclick="toggleGit()">&lt;</button>
<div class="git-panel-inner">
<div class="git-section">
<div class="git-header">RECENT COMMITS</div>
<div class="branch-name" id="branchName"></div>
<div class="commit-list" id="commitList"></div>
</div>
<div class="file-browser" id="fileBrowserResizer">
<div class="file-browser-content">
<div class="browser-header">
<span class="browser-path" id="currentPath" onclick="editPath()"></span>
<input type="text" class="browser-path-input" id="pathInput" onkeydown="handlePathKey(event)" onblur="cancelPathEdit()">
<div class="browser-icons">
<button class="browser-btn" onclick="goUp()" title="Up one level">&#x2191;</button>
<button class="browser-btn" onclick="refreshTree(true)" title="Refresh">&#x21BB;</button>
<button class="browser-btn" onclick="toggleSearch()" title="Search">&#x1F50D;</button>
</div>
<div class="search-box" id="searchBox"><input type="text" id="searchInput" placeholder="Search..." oninput="filterTree()"><button class="search-clear" id="searchClear" onclick="clearSearch()" title="Clear">&#x2715;</button></div>
</div>
<div class="file-tree" id="fileTree"><div class="no-results" id="noResults">No results</div></div>
</div>
</div>
</div>
<div class="git-resizer" id="gitResizer"></div>
</div>
<div class="diff-wrapper">
<div class="resizer" id="resizer"></div>
<div class="diff-container" id="container">
<div class="left-panel" id="leftPanel">
<div class="panel-header">OLD: {html.escape(old_file)}</div>
<div id="leftLines"></div>
</div>
<div class="right-panel" id="rightPanel">
<div class="panel-header">NEW: {html.escape(new_file)} (editable)</div>
<div class="editor-wrapper">
<div class="line-numbers" id="lineNumbers"></div>
<textarea class="editor" id="editor">{html.escape(new_content)}</textarea>
</div>
</div>
</div>
</div>
</div>
<script>
var fileName = {json.dumps(os.path.basename(new_file))};
var oldLines = {old_lines_js};
var newLines = {new_lines_js};
var commits = {commits_js};
var currentBranch = {branch_js};
var gitStatus = {git_status_js};
var folderTrees = {folder_trees_js};
var currentDir = {current_dir_js};
var originalDir = currentDir;
var currentFile = {current_file_js};

var selectedCommitIdx = -1;
var currentOldLines = oldLines;

function buildCommitList() {{
    document.getElementById("branchName").textContent = currentBranch ? "* " + currentBranch : "";
    var h = "";

    // Show status message if no commits
    if (commits.length === 0) {{
        var msg = "";
        if (gitStatus === "no_repo") msg = "Not a git repository";
        else if (gitStatus === "ignored") msg = "File is gitignored";
        else if (gitStatus === "untracked") msg = "File not tracked";
        else if (gitStatus === "no_history") msg = "No commits for this file";
        else if (gitStatus === "error") msg = "Git error";
        h = "<div class=git-status>" + msg + "</div>";
    }} else {{
        commits.forEach(function(c, idx) {{
            h += "<div class=commit data-idx=" + idx + "><div class=commit-id>" + c.id + "</div><div class=commit-msg>" + c.msg.replace(/</g,"&lt;").replace(/>/g,"&gt;") + "</div><div class=commit-date>" + c.date + "</div></div>";
        }});
    }}
    document.getElementById("commitList").innerHTML = h;

    // Add double-click handlers
    document.querySelectorAll(".commit").forEach(function(el) {{
        el.addEventListener("dblclick", function() {{
            var idx = parseInt(this.getAttribute("data-idx"));
            selectCommit(idx);
        }});
    }});
}}

function selectCommit(idx) {{
    // Remove previous selection
    document.querySelectorAll(".commit.selected").forEach(function(el) {{
        el.classList.remove("selected");
    }});

    selectedCommitIdx = idx;
    var commit = commits[idx];

    // Highlight selected commit
    document.querySelectorAll(".commit")[idx].classList.add("selected");

    // Update left panel with this commit's content
    if (commit.content && commit.content.length > 0) {{
        currentOldLines = commit.content;
        document.querySelector(".left-panel .panel-header").textContent = "OLD: " + commit.id + " - " + commit.msg.substring(0, 30);
        buildLeftPanel();
    }}
}}

function toggleGit(e) {{
    var panel = document.getElementById("gitPanel");
    var btn = panel.querySelector(".git-toggle");
    panel.classList.toggle("collapsed");
    btn.textContent = panel.classList.contains("collapsed") ? ">" : "<";
    if (panel.classList.contains("collapsed")) {{
        panel.style.width = "";
        panel.style.minWidth = "";
    }}
}}

// Make entire collapsed panel clickable
document.getElementById("gitPanel").addEventListener("click", function(e) {{
    if (this.classList.contains("collapsed") && e.target !== document.querySelector(".git-toggle")) {{
        toggleGit();
    }}
}});

// File browser functions
var serverUrl = "http://localhost:8765";
var serverToken = {server_token_js};
var serverOnline = false;

function getCurrentTree() {{
    var normalized = currentDir.replace(/\\\\/g, "/");
    for (var key in folderTrees) {{
        if (key.replace(/\\\\/g, "/") === normalized) {{
            return folderTrees[key];
        }}
    }}
    return [];
}}
var displayedTree = getCurrentTree();

function loadFile(filePath, fileName) {{
    fetch(serverUrl + "?file=" + encodeURIComponent(filePath) + "&token=" + encodeURIComponent(serverToken))
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
            if (data.error) {{
                console.error("Failed to load file:", data.error);
                return;
            }}
            // Update current file reference
            currentFile = filePath;
            document.getElementById("fileName").textContent = fileName;
            document.title = "Diff: " + fileName;

            // Highlight current file in tree
            document.querySelectorAll(".tree-file.current").forEach(function(el) {{
                el.classList.remove("current");
            }});
            document.querySelectorAll(".tree-file").forEach(function(el) {{
                if (el.title === filePath || el.title.replace(/\\\\/g, "/") === filePath.replace(/\\\\/g, "/")) {{
                    el.classList.add("current");
                }}
            }});

            // Right panel: current file content
            newLines = data.content.split("\\n");
            document.getElementById("editor").value = data.content;
            document.querySelector(".right-panel .panel-header").textContent = "NEW: " + fileName + " (editable)";
            updateLineNumbers();

            // Left panel: git version or blank
            if (data.git_content) {{
                currentOldLines = data.git_content.split("\\n");
                document.querySelector(".left-panel .panel-header").textContent = "OLD: " + fileName + " (HEAD)";
            }} else {{
                currentOldLines = [];
                document.querySelector(".left-panel .panel-header").textContent = "OLD: (no git history)";
            }}
            buildLeftPanel();

            // Update git panel with file's commits
            if (data.commits !== undefined) {{
                commits = data.commits;
                currentBranch = data.branch || "";
                gitStatus = data.git_status || "ok";
                selectedCommitIdx = -1;
                buildCommitList();
            }}

            // Clear status message
            document.getElementById("status").textContent = "";
        }})
        .catch(function(err) {{
            console.error("Failed to load file:", err);
        }});
}}

function fetchFolder(path, callback) {{
    fetch(serverUrl + "?path=" + encodeURIComponent(path) + "&token=" + encodeURIComponent(serverToken))
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
            if (data.tree) {{
                serverOnline = true;
                folderTrees[path] = data.tree;
                callback(data.tree);
            }} else {{
                callback(null);
            }}
        }})
        .catch(function() {{
            serverOnline = false;
            callback(null);
        }});
}}

function hasMatch(item, filter) {{
    if (item.name.toLowerCase().indexOf(filter) !== -1) return true;
    if (item.type === "dir" && item.children) {{
        for (var i = 0; i < item.children.length; i++) {{
            if (hasMatch(item.children[i], filter)) return true;
        }}
    }}
    return false;
}}

function buildFileTree(items, container, filter, isRoot) {{
    if (isRoot) {{
        container.innerHTML = "<div class=no-results id=noResults>No results</div>";
    }}
    var matchCount = 0;
    items.forEach(function(item) {{
        if (filter) {{
            if (!hasMatch(item, filter)) return;
        }}
        matchCount++;
        var div = document.createElement("div");
        if (item.type === "dir") {{
            var nameMatch = item.name.toLowerCase().indexOf(filter) !== -1;
            div.className = "tree-item tree-dir";
            div.innerHTML = "<span class=tree-toggle>" + (filter ? "-" : "+") + "</span>" + item.name;
            div.onclick = function(e) {{
                e.stopPropagation();
                var children = this.nextElementSibling;
                if (children) {{
                    children.classList.toggle("open");
                    this.querySelector(".tree-toggle").textContent = children.classList.contains("open") ? "-" : "+";
                }}
            }};
            container.appendChild(div);
            if (item.children && item.children.length > 0) {{
                var childDiv = document.createElement("div");
                childDiv.className = "tree-children" + (filter ? " open" : "");
                buildFileTree(item.children, childDiv, filter, false);
                container.appendChild(childDiv);
            }}
        }} else {{
            div.className = "tree-item tree-file";
            if (item.path === currentFile) div.className += " current";
            div.textContent = item.name;
            div.title = item.path;
            div.onclick = function(e) {{
                e.stopPropagation();
                loadFile(item.path, item.name);
            }};
            container.appendChild(div);
        }}
    }});
    if (isRoot) {{
        var noRes = document.getElementById("noResults");
        if (noRes) noRes.className = matchCount === 0 ? "no-results show" : "no-results";
    }}
}}

function updatePath() {{
    var parts = currentDir.replace(/\\\\/g, "/").split("/").filter(function(p) {{ return p; }});
    var display = parts.slice(-3).join("/");
    document.getElementById("currentPath").textContent = display;
}}

function editPath() {{
    var pathSpan = document.getElementById("currentPath");
    var pathInput = document.getElementById("pathInput");
    pathSpan.className = "browser-path hidden";
    pathInput.className = "browser-path-input show";
    pathInput.value = currentDir.replace(/\\\\/g, "/");
    pathInput.focus();
    pathInput.select();
}}

function cancelPathEdit() {{
    var pathSpan = document.getElementById("currentPath");
    var pathInput = document.getElementById("pathInput");
    pathSpan.className = "browser-path";
    pathInput.className = "browser-path-input";
}}

function handlePathKey(e) {{
    if (e.key === "Escape") {{
        cancelPathEdit();
    }} else if (e.key === "Enter") {{
        var newPath = document.getElementById("pathInput").value.replace(/\\\\/g, "/");
        navigateToPath(newPath);
        cancelPathEdit();
    }}
}}

function navigateToPath(path) {{
    // Try server first
    fetchFolder(path, function(data) {{
        if (data) {{
            currentDir = path;
            displayedTree = data;
            refreshTree();
        }} else {{
            // Try pre-loaded
            for (var key in folderTrees) {{
                if (key.replace(/\\\\/g, "/") === path) {{
                    currentDir = path;
                    displayedTree = folderTrees[key];
                    refreshTree();
                    return;
                }}
            }}
            // Path not found
            var pathSpan = document.getElementById("currentPath");
            var oldText = pathSpan.textContent;
            pathSpan.textContent = "Path not found";
            pathSpan.style.color = "#f48771";
            setTimeout(function() {{
                pathSpan.textContent = oldText;
                pathSpan.style.color = "";
            }}, 2000);
        }}
    }});
}}

function refreshTree(forceServer) {{
    var tree = document.getElementById("fileTree");
    if (forceServer) {{
        tree.innerHTML = "<div class='no-results show'>Loading...</div>";
        fetchFolder(currentDir, function(data) {{
            if (data) {{
                displayedTree = data;
            }}
            tree.innerHTML = "";
            buildFileTree(displayedTree, tree, "", true);
            updatePath();
        }});
    }} else {{
        tree.innerHTML = "";
        buildFileTree(displayedTree, tree, "", true);
        updatePath();
    }}
}}

function goUp() {{
    var parts = currentDir.replace(/\\\\/g, "/").split("/").filter(function(p) {{ return p; }});
    if (parts.length <= 1) return;
    parts.pop();
    var newDir = parts[0] + ":/" + parts.slice(1).join("/");
    if (parts.length === 1) newDir = parts[0] + ":/";

    // Try server first, then fall back to pre-loaded
    currentDir = newDir;
    fetchFolder(newDir, function(data) {{
        if (data) {{
            displayedTree = data;
            refreshTree();
        }} else {{
            // Fall back to pre-loaded
            var parentTree = null;
            for (var key in folderTrees) {{
                if (key.replace(/\\\\/g, "/") === newDir) {{
                    parentTree = folderTrees[key];
                    break;
                }}
            }}
            if (parentTree) {{
                displayedTree = parentTree;
                refreshTree();
            }} else {{
                // No data available
                displayedTree = [];
                refreshTree();
            }}
        }}
    }});
}}

function toggleSearch() {{
    var box = document.getElementById("searchBox");
    box.classList.toggle("show");
    if (box.classList.contains("show")) {{
        document.getElementById("searchInput").focus();
    }} else {{
        clearSearch();
    }}
}}

function clearSearch() {{
    document.getElementById("searchInput").value = "";
    document.getElementById("searchClear").className = "search-clear";
    refreshTree();
}}

function filterTree() {{
    var filter = document.getElementById("searchInput").value.toLowerCase();
    var clearBtn = document.getElementById("searchClear");
    clearBtn.className = filter ? "search-clear show" : "search-clear";
    var tree = document.getElementById("fileTree");
    tree.innerHTML = "";
    buildFileTree(displayedTree, tree, filter, true);
}}

// Git panel resizer
var gitResizing = false;
var gitPanel = document.getElementById("gitPanel");
var gitResizer = document.getElementById("gitResizer");

gitResizer.addEventListener("mousedown", function(e) {{
    gitResizing = true;
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none";
}});

document.addEventListener("mousemove", function(e) {{
    if (!gitResizing) return;
    var newWidth = e.clientX - gitPanel.getBoundingClientRect().left;
    if (newWidth > 100 && newWidth < 400) {{
        gitPanel.style.width = newWidth + "px";
    }}
}});

document.addEventListener("mouseup", function() {{
    if (gitResizing) {{
        gitResizing = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
    }}
    if (browserResizing) {{
        browserResizing = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
    }}
}});

// File browser vertical resizer
var browserResizing = false;
var fileBrowserResizer = document.getElementById("fileBrowserResizer");
var gitSection = document.querySelector(".git-section");

fileBrowserResizer.addEventListener("mousedown", function(e) {{
    if (e.offsetY < 6) {{
        browserResizing = true;
        document.body.style.cursor = "ns-resize";
        document.body.style.userSelect = "none";
    }}
}});

document.addEventListener("mousemove", function(e) {{
    if (!browserResizing) return;
    var panelRect = gitPanel.getBoundingClientRect();
    var y = e.clientY - panelRect.top - 30;
    var maxY = panelRect.height - 100;
    if (y > 50 && y < maxY) {{
        gitSection.style.height = y + "px";
        gitSection.style.flex = "none";
    }}
}});

function buildLeftPanel() {{
    var leftHtml = "";
    var maxLines = Math.max(currentOldLines.length, newLines.length);
    for (var i = 0; i < maxLines; i++) {{
        var num = i + 1;
        var oldLine = i < currentOldLines.length ? currentOldLines[i] : "";
        var newLine = i < newLines.length ? newLines[i] : "";
        var escaped_old = oldLine.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");

        var leftClass = "";
        if (oldLine !== newLine) {{
            if (i >= currentOldLines.length) leftClass = " added";
            else if (i >= newLines.length) leftClass = " removed";
            else leftClass = " changed-left";
        }}

        leftHtml += "<div class=line-row" + leftClass + "><div class=line-num>" + (i < currentOldLines.length ? num : "") + "</div><div class=line-content>" + escaped_old + "</div></div>";
    }}
    document.getElementById("leftLines").innerHTML = leftHtml;
}}

// Resizer
var isResizing = false;
var leftPanel = document.getElementById("leftPanel");
var resizer = document.getElementById("resizer");
var container = document.getElementById("container");

resizer.addEventListener("mousedown", function(e) {{
    isResizing = true;
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none";
}});

document.addEventListener("mousemove", function(e) {{
    if (!isResizing) return;
    var rect = container.getBoundingClientRect();
    var x = e.clientX - rect.left;
    var percent = (x / rect.width) * 100;
    if (percent > 15 && percent < 85) {{
        leftPanel.style.width = percent + "%";
        resizer.style.left = percent + "%";
    }}
}});

document.addEventListener("mouseup", function() {{
    if (isResizing) {{
        isResizing = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
    }}
}});

// Save
function saveFile() {{
    var text = document.getElementById("editor").value;
    var status = document.getElementById("status");

    // Try server first for direct save
    fetch(serverUrl, {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{path: currentFile, content: text, token: serverToken}})
    }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
        if (data.success) {{
            status.textContent = "Saved!";
            status.style.color = "#89d185";
        }} else {{
            throw new Error(data.error);
        }}
    }})
    .catch(function(err) {{
        // Fall back to download
        var timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
        var newName = fileName.replace(/(\\.[^.]+)$/, "_edited_" + timestamp + "$1");
        if (newName === fileName) newName = fileName + "_edited_" + timestamp;

        var blob = new Blob([text], {{type: "text/plain"}});
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = newName;
        a.click();
        URL.revokeObjectURL(a.href);
        status.textContent = "Downloaded: " + newName;
        status.style.color = "#dcdcaa";
    }});
}}

// Line numbers
var editor = document.getElementById("editor");
var lineNumbers = document.getElementById("lineNumbers");

function updateLineNumbers() {{
    var lines = editor.value.split("\\n").length;
    var nums = "";
    for (var i = 1; i <= lines; i++) {{
        nums += i + "\\n";
    }}
    lineNumbers.textContent = nums;
}}

editor.addEventListener("scroll", function() {{
    lineNumbers.scrollTop = editor.scrollTop;
}});

editor.addEventListener("input", updateLineNumbers);

// Scroll sync between panels
leftPanel.addEventListener("scroll", function() {{
    editor.scrollTop = leftPanel.scrollTop;
    lineNumbers.scrollTop = leftPanel.scrollTop;
}});
editor.addEventListener("scroll", function() {{
    leftPanel.scrollTop = editor.scrollTop;
}});

// Init
buildLeftPanel();
buildCommitList();
updateLineNumbers();
refreshTree();
</script>
</body></html>'''

out_path = os.path.join(os.path.dirname(__file__), 'diff_viewer.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(os.path.abspath(out_path))
