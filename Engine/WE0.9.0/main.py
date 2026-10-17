from ursina import *
import sys
import os
import json

# Get project name before initializing Ursina
project_name = "No project opened"
project_path = None

if "--project" in sys.argv:
    try:
        project_index = sys.argv.index("--project") + 1
        project_path = os.path.abspath(sys.argv[project_index])

        project_json = os.path.join(project_path, "project.json")

        with open(project_json, "r", encoding="utf-8") as file:
            project_data = json.load(file)

        project_name = project_data.get("name", "Unnamed Project")

    except (IndexError, OSError, json.JSONDecodeError) as error:
        project_name = "Failed to load project"
        print(f"Project loading error: {error}")

app = Ursina(title=f"Wisher Engine Editor - {project_name}")

window.cog_button.visible = False
window.cog_menu = None
window.entity_counter.visible = False
window.fps_counter.visible = False
window.collider_counter.visible = False
window.exit_button.disabled = True
window.exit_button.visible = False

# Load the project's scene.py
if project_path:
    scene_file = os.path.join(project_path, "scene.py")

    if os.path.isfile(scene_file):
        try:
            with open(scene_file, "r", encoding="utf-8") as file:
                scene_code = file.read()

            scene_globals = {
                "__name__": "__main__",
                "__file__": scene_file,
                "__builtins__": __builtins__,
            }

            exec(compile(scene_code, scene_file, "exec"), scene_globals)

            print(f"Loaded scene: {scene_file}")

        except Exception as error:
            print(f"Scene loading error: {error}")
    else:
        print(f"Scene file not found: {scene_file}")

EditorCamera()
camera.fov_setter(90)

app.run()
