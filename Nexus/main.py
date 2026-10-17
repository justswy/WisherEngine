
import tkinter as tk
from tkinter import messagebox, simpledialog
import os
import json
import re
import sys
import subprocess
import urllib.request
import urllib.error
import urllib.parse
import zipfile
import tempfile
import shutil
import threading

# =====================================
# WISHER ENGINE NEXUS
# GitHub repository engine installer
# =====================================
GITHUB_REPO = "justswy/WisherEngine"
GITHUB_BRANCH = "main"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}"
GITHUB_VERSION = None

BG = "#36454F"
PANEL = "#405563"
HOVER = "#506A7A"
TEXT = "#FFFFFF"
MUTED = "#D0D8DD"
ACCENT = "#80CBC4"
ERROR = "#FF8A80"
WIDTH = 900
HEIGHT = 500

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENGINES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Engines")
PROJECTS_DIR = os.path.join(BASE_DIR, "Projects")
os.makedirs(ENGINES_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

root = tk.Tk()
root.title("Wisher Engine Nexus")
root.overrideredirect(True)
root.configure(bg=BG)
x = (root.winfo_screenwidth() - WIDTH) // 2
y = (root.winfo_screenheight() - HEIGHT) // 2
root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")

# =====================================
# WINDOW DRAGGING
# =====================================
drag_data = {"x": 0, "y": 0}

def start_drag(event):
    drag_data["x"] = event.x_root - root.winfo_x()
    drag_data["y"] = event.y_root - root.winfo_y()

def drag_window(event):
    root.geometry(
        f"+{event.x_root - drag_data['x']}"
        f"+{event.y_root - drag_data['y']}"
    )

# =====================================
# HELPERS
# =====================================
def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

def parse_version(version):
    version = str(version).strip().lstrip("vV")
    if not re.fullmatch(r"\d+(?:\.\d+)*", version):
        return ()
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return ()

def get_installed_versions():
    versions = []
    if not os.path.isdir(ENGINES_DIR):
        return versions
    for folder in os.listdir(ENGINES_DIR):
        engine_dir = os.path.join(ENGINES_DIR, folder)
        metadata_path = os.path.join(engine_dir, "engine.json")
        editor_path = os.path.join(engine_dir, "dist", "editor.exe")
        if not os.path.isfile(metadata_path):
            continue
        if not os.path.isfile(editor_path):
            continue
        metadata = read_json(metadata_path)
        version = str(metadata.get("version", "")).strip()
        if version and parse_version(version):
            versions.append(version)
    return sorted(versions, key=parse_version, reverse=True)

def is_version_installed(version):
    engine_dir = os.path.join(ENGINES_DIR, f"WE{version}")
    return (
        os.path.isfile(os.path.join(engine_dir, "engine.json"))
        and os.path.isfile(os.path.join(engine_dir, "dist", "editor.exe"))
    )

# =====================================
# GITHUB REPOSITORY DOWNLOAD
# =====================================
def fetch_latest_release():
    """Find the highest-version WisherEngine-X.X.X.zip in the repository."""
    global GITHUB_VERSION
    request = urllib.request.Request(
        GITHUB_API,
        headers={"User-Agent": "Wisher-Engine-Nexus"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise RuntimeError(
                "Could not find the repository or its main branch. "
                "Check the repository name and branch."
            ) from error
        raise RuntimeError(f"GitHub API returned HTTP {error.code}.") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not connect to GitHub: {error.reason}") from error

    if data.get("truncated"):
        raise RuntimeError("GitHub returned an incomplete repository file list.")

    matches = []
    for item in data.get("tree", []):
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        filename = path.rsplit("/", 1)[-1]
        match = re.fullmatch(
            r"WisherEngine-(\d+(?:\.\d+)+)\.zip",
            filename,
            re.IGNORECASE
        )
        if not match:
            continue
        version = match.group(1)
        parsed_version = parse_version(version)
        if parsed_version:
            matches.append((parsed_version, version, path))

    if not matches:
        raise RuntimeError(
            "No WisherEngine-X.X.X.zip was found in the repository's "
            f"'{GITHUB_BRANCH}' branch. Add a versioned ZIP to GitHub first."
        )

    _, version, path = max(matches, key=lambda item: item[0])
    GITHUB_VERSION = version
    asset_name = path.rsplit("/", 1)[-1]
    download_url = f"{GITHUB_RAW}/{urllib.parse.quote(path, safe='/')}"
    return version, download_url, asset_name

# =====================================
# PROJECT MANAGEMENT
# =====================================
def open_project(project_dir):
    project_file = os.path.join(project_dir, "project.json")
    if not os.path.isfile(project_file):
        messagebox.showerror(
            "Project Error",
            "This folder does not contain project.json.",
            parent=root
        )
        return

    project_data = read_json(project_file)
    version = str(project_data.get("editor version", "")).strip()
    if not version:
        messagebox.showerror(
            "Project Error",
            "The project does not specify an engine version.",
            parent=root
        )
        return

    engine_dir = os.path.join(ENGINES_DIR, f"WE{version}")
    editor_path = os.path.join(engine_dir, "dist", "editor.exe")
    if not os.path.isfile(editor_path):
        messagebox.showerror(
            "Engine Missing",
            f"Wisher Engine {version} is not installed.\n\n"
            "Install that version before opening this project.",
            parent=root
        )
        return

    try:
        subprocess.Popen(
            [editor_path, "--project", os.path.abspath(project_dir)],
            cwd=engine_dir
        )
        root.destroy()
    except OSError as error:
        messagebox.showerror(
            "Launch Error",
            f"Could not launch the editor:\n{error}",
            parent=root
        )

def create_new_project():
    if not GITHUB_VERSION:
        messagebox.showerror(
            "Version Not Ready",
            "Nexus is still checking GitHub for the latest engine version.\n\n"
            "Wait for the version check to finish, then try again.",
            parent=root
        )
        return

    name = simpledialog.askstring(
        "New Project",
        "Enter your project name:",
        parent=root
    )
    if name is None:
        return

    name = name.strip()
    if not name:
        messagebox.showerror(
            "Invalid Name",
            "The project name cannot be empty.",
            parent=root
        )
        return

    if (
        name in (".", "..")
        or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
        or name.endswith((" ", "."))
    ):
        messagebox.showerror(
            "Invalid Name",
            "That name is not valid for a Windows folder.",
            parent=root
        )
        return

    project_dir = os.path.abspath(os.path.join(PROJECTS_DIR, name))
    projects_root = os.path.abspath(PROJECTS_DIR)
    if os.path.commonpath([projects_root, project_dir]) != projects_root:
        messagebox.showerror(
            "Invalid Name",
            "That project path is not allowed.",
            parent=root
        )
        return

    if os.path.exists(project_dir):
        messagebox.showerror(
            "Project Exists",
            "A project with that name already exists.",
            parent=root
        )
        return

    try:
        os.makedirs(project_dir)
        with open(
            os.path.join(project_dir, "project.json"),
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                {"name": name, "editor version": GITHUB_VERSION},
                file,
                indent=4
            )

        with open(
            os.path.join(project_dir, "scene.py"),
            "w",
            encoding="utf-8"
        ) as file:
            file.write(
                "from ursina import *\n\n"
                "app = Ursina()\n\n"
                "Sky()\n\n"
                "# Start building your project here.\n\n"
                "app.run()\n"
            )
    except OSError as error:
        shutil.rmtree(project_dir, ignore_errors=True)
        messagebox.showerror(
            "Project Error",
            f"Could not create the project:\n{error}",
            parent=root
        )
        return

    refresh_projects()
    messagebox.showinfo(
        "Project Created",
        f"Created project '{name}'.",
        parent=root
    )

# =====================================
# DOWNLOAD AND VALIDATE ZIP
# =====================================
def download_file(url, destination):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Wisher-Engine-Nexus"}
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            with open(destination, "wb") as file:
                shutil.copyfileobj(response, file)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise RuntimeError(
                "The engine ZIP was not found at the GitHub URL.\n\n"
                "Check that the versioned ZIP still exists in the repository."
            ) from error
        raise

    if not zipfile.is_zipfile(destination):
        raise RuntimeError(
            "GitHub did not return a valid ZIP archive.\n\n"
            "The file must be the complete engine ZIP, not "
            "a GitHub HTML error page."
        )

# =====================================
# SAFE ZIP EXTRACTION
# =====================================
def safe_extract_zip(zip_path, destination):
    destination_real = os.path.realpath(destination)
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            target = os.path.realpath(
                os.path.join(destination, member.filename)
            )
            if os.path.commonpath([destination_real, target]) != destination_real:
                raise RuntimeError("The engine ZIP contains an unsafe file path.")
        archive.extractall(destination)

def locate_engine_root(directory):
    for current_root, dirs, files in os.walk(directory):
        if (
            "engine.json" in files
            and os.path.isfile(os.path.join(current_root, "dist", "editor.exe"))
        ):
            return current_root
    return None

# =====================================
# INSTALL ENGINE
# =====================================
def install_engine_worker():
    stage_dir = None
    try:
        version, download_url, asset_name = fetch_latest_release()
        if is_version_installed(version):
            root.after(
                0,
                lambda v=version: finish_install(
                    f"Wisher Engine {v} is already installed.",
                    True
                )
            )
            return

        stage_dir = tempfile.mkdtemp(prefix="wisher_nexus_", dir=BASE_DIR)
        zip_path = os.path.join(stage_dir, asset_name)
        extract_dir = os.path.join(stage_dir, "extracted")
        os.makedirs(extract_dir)

        root.after(
            0,
            lambda n=asset_name: status_label.configure(
                text=f"Downloading {n} from GitHub...",
                fg=MUTED
            )
        )

        download_file(download_url, zip_path)
        safe_extract_zip(zip_path, extract_dir)
        engine_root = locate_engine_root(extract_dir)
        if engine_root is None:
            raise RuntimeError(
                "The ZIP is missing the expected engine files.\n\n"
                "It must contain engine.json and dist/editor.exe."
            )

        metadata = read_json(os.path.join(engine_root, "engine.json"))
        archive_version = str(metadata.get("version", "")).strip()
        if not parse_version(archive_version):
            raise RuntimeError("engine.json is missing a valid version number.")
        if archive_version != version:
            raise RuntimeError(
                "The ZIP filename version and engine.json version differ.\n\n"
                f"ZIP version: {version}\n"
                f"Engine version: {archive_version}"
            )

        target_dir = os.path.join(ENGINES_DIR, f"WE{version}")
        backup_dir = target_dir + ".backup"
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        if os.path.exists(target_dir):
            os.replace(target_dir, backup_dir)

        try:
            shutil.copytree(engine_root, target_dir)
        except Exception:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            if os.path.exists(backup_dir):
                os.replace(backup_dir, target_dir)
            raise

        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir, ignore_errors=True)

        root.after(
            0,
            lambda v=version: finish_install(
                f"Wisher Engine {v} installed successfully!",
                True
            )
        )
    except Exception as error:
        error_text = str(error)
        try:
            root.after(
                0,
                lambda text=error_text: finish_install(
                    f"Installation failed:\n\n{text}",
                    False
                )
            )
        except tk.TclError:
            pass
    finally:
        if stage_dir:
            shutil.rmtree(stage_dir, ignore_errors=True)

def finish_install(message, success):
    install_button.configure(state="normal", text="Install Latest Engine")
    status_label.configure(
        text="Ready" if success else "Installation failed",
        fg=ACCENT if success else ERROR
    )
    refresh_engines()
    if success:
        messagebox.showinfo("Wisher Engine Nexus", message, parent=root)
    else:
        messagebox.showerror("Wisher Engine Nexus", message, parent=root)

def install_latest_engine():
    install_button.configure(state="disabled", text="Installing...")
    status_label.configure(text="Checking GitHub repository...", fg=MUTED)
    threading.Thread(target=install_engine_worker, daemon=True).start()

# =====================================
# SCROLLABLE PANELS
# =====================================
def create_scrollable_column(parent):
    outer = tk.Frame(parent, bg=PANEL)
    canvas = tk.Canvas(
        outer,
        bg=PANEL,
        highlightthickness=0,
        borderwidth=0
    )
    scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=PANEL)
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def update_scroll_region(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def resize_inner(event):
        canvas.itemconfigure(window_id, width=event.width)

    inner.bind("<Configure>", update_scroll_region)
    canvas.bind("<Configure>", resize_inner)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return outer, inner

def make_button(parent, text, command, bg=PANEL, fg=TEXT):
    button = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=HOVER,
        activeforeground=TEXT,
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=10,
        pady=7
    )
    button.bind("<Enter>", lambda event: button.configure(bg=HOVER))
    button.bind("<Leave>", lambda event: button.configure(bg=bg))
    return button

# =====================================
# TITLE BAR
# =====================================
title_bar = tk.Frame(root, bg="#263640", height=38)
title_bar.pack(fill="x")
title_bar.pack_propagate(False)
title_label = tk.Label(
    title_bar,
    text="Wisher Engine Nexus",
    bg="#263640",
    fg=TEXT,
    font=("Segoe UI", 10)
)
title_label.pack(side="left", padx=14)
close_button = tk.Button(
    title_bar,
    text="✕",
    command=root.destroy,
    bg="#263640",
    fg=TEXT,
    activebackground="#B85450",
    activeforeground=TEXT,
    relief="flat",
    bd=0,
    width=5,
    cursor="hand2"
)
close_button.pack(side="right", fill="y")
for widget in (title_bar, title_label):
    widget.bind("<Button-1>", start_drag)
    widget.bind("<B1-Motion>", drag_window)

# =====================================
# MAIN LAYOUT
# =====================================
main = tk.Frame(root, bg=BG)
main.pack(fill="both", expand=True, padx=14, pady=12)
left_panel = tk.Frame(main, bg=PANEL)
right_panel = tk.Frame(main, bg=PANEL)
left_panel.pack(side="left", fill="both", expand=True, padx=(0, 7))
right_panel.pack(side="right", fill="both", expand=True, padx=(7, 0))

# =====================================
# ENGINE PANEL
# =====================================
tk.Label(
    left_panel,
    text="Engines",
    bg=PANEL,
    fg=TEXT,
    font=("Segoe UI", 13, "bold")
).pack(anchor="w", padx=12, pady=(12, 5))

install_button = make_button(
    left_panel,
    "Install Latest Engine",
    install_latest_engine,
    bg="#287D78"
)
install_button.pack(fill="x", padx=12, pady=(0, 5))

status_label = tk.Label(
    left_panel,
    text="Ready",
    bg=PANEL,
    fg=MUTED,
    font=("Segoe UI", 9),
    anchor="w",
    wraplength=380,
    justify="left"
)
status_label.pack(fill="x", padx=12, pady=(0, 8))

engine_outer, engine_cards = create_scrollable_column(left_panel)
engine_outer.pack(fill="both", expand=True, padx=8, pady=(0, 10))

def refresh_engines():
    for child in engine_cards.winfo_children():
        child.destroy()
    versions = get_installed_versions()
    if not versions:
        tk.Label(
            engine_cards,
            text="No engines installed yet.",
            bg=PANEL,
            fg=MUTED
        ).pack(anchor="w", padx=8, pady=8)
        return

    for version in versions:
        card = tk.Frame(engine_cards, bg=BG, padx=9, pady=8)
        card.pack(fill="x", padx=5, pady=4)
        tk.Label(
            card,
            text=f"Wisher Engine {version}",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")
        tk.Label(
            card,
            text=os.path.join("Engines", f"WE{version}"),
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(2, 5))
        make_button(
            card,
            "Open Engine Folder",
            lambda v=version: os.startfile(os.path.join(ENGINES_DIR, f"WE{v}"))
        ).pack(anchor="w")

# =====================================
# PROJECT PANEL
# =====================================
tk.Label(
    right_panel,
    text="Projects",
    bg=PANEL,
    fg=TEXT,
    font=("Segoe UI", 13, "bold")
).pack(anchor="w", padx=12, pady=(12, 8))

make_button(
    right_panel,
    "+ New Project",
    create_new_project,
    bg="#287D78"
).pack(fill="x", padx=12, pady=(0, 8))

project_outer, projects_list = create_scrollable_column(right_panel)
project_outer.pack(fill="both", expand=True, padx=8, pady=(0, 10))

def refresh_projects():
    for child in projects_list.winfo_children():
        child.destroy()
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    found_project = False

    for name in sorted(os.listdir(PROJECTS_DIR), key=str.lower):
        project_dir = os.path.join(PROJECTS_DIR, name)
        if not os.path.isdir(project_dir):
            continue
        project_file = os.path.join(project_dir, "project.json")
        if not os.path.isfile(project_file):
            continue

        found_project = True
        project_data = read_json(project_file)
        version = project_data.get("editor version", "Unknown")
        card = tk.Frame(projects_list, bg=BG, padx=9, pady=8)
        card.pack(fill="x", padx=5, pady=4)
        tk.Label(
            card,
            text=name,
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")
        tk.Label(
            card,
            text=f"Engine version: {version}",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(2, 5))
        make_button(
            card,
            "Open Project",
            lambda path=project_dir: open_project(path)
        ).pack(anchor="w")

    if not found_project:
        tk.Label(
            projects_list,
            text="No projects yet. Create one above!",
            bg=PANEL,
            fg=MUTED,
            wraplength=330
        ).pack(anchor="w", padx=8, pady=8)

# =====================================
# AUTOMATIC REPOSITORY CHECK
# =====================================
def check_for_updates_worker():
    try:
        version, download_url, asset_name = fetch_latest_release()
        if is_version_installed(version):
            text = f"Engine {version} is installed"
        else:
            text = f"Engine {version} is available to install"
        root.after(
            0,
            lambda msg=text: status_label.configure(text=msg, fg=ACCENT)
        )
    except Exception as error:
        error_text = str(error)
        try:
            root.after(
                0,
                lambda msg=error_text: status_label.configure(
                    text=f"Version check failed: {msg}",
                    fg=ERROR
                )
            )
        except tk.TclError:
            pass

def check_for_updates():
    threading.Thread(target=check_for_updates_worker, daemon=True).start()

# =====================================
# START
# =====================================
refresh_engines()
refresh_projects()
check_for_updates()
root.mainloop()
