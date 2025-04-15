from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Shared scene state
scene = {
    "points": [],
    "frustums": [],
    "axes": [],
    "meshes": [],           # Only used for the initial mesh
    "updated_mesh": None,   # Last updated mesh (will replace the previous)
    "add_global_axes": False
}

@app.route("/")
def index():
    return render_template("viewer.html")  # Loads modular viewer (main.js)

@app.route("/scene", methods=["GET"])
def get_scene():
    return jsonify({
        "points": scene["points"],
        "frustums": scene["frustums"],
        "axes": scene["axes"],
        "meshes": scene["meshes"],
        "updated_mesh": scene["updated_mesh"],
        "add_global_axes": scene["add_global_axes"]
    })


@app.route("/update_pointcloud", methods=["POST"])
def update_pointcloud():
    data = request.json
    scene["points"] = data.get("points", [])
    return "Point cloud updated", 200

@app.route("/add_frustum", methods=["POST"])
def add_frustum():
    data = request.json
    pose = data["pose"]
    color = data.get("color", "#00ff00")  # Default green if not provided
    scene["frustums"].append({"pose": pose, "color": color})
    return "Frustum added", 200

@app.route("/add_object_axis", methods=["POST"])
def add_object_axis():
    data = request.json
    scene["axes"].append({
        "pose": data["pose"],
        "label": data.get("label", "Object")
    })
    return "Object axis added", 200

@app.route("/add_global_axes", methods=["POST"])
def add_global_axes():
    scene["add_global_axes"] = True
    return "Global axes flag set", 200

@app.route("/load_scene", methods=["POST"])
def load_scene():
    data = request.json
    scene["points"] = data.get("points", [])
    scene["meshes"] = []

    mesh = data.get("mesh")
    if mesh:
        scene["meshes"].append({
            "mesh": mesh,
            "label": "initial"
        })
        
    scene["add_global_axes"] = True

    return "Scene loaded", 200

@app.route("/add_mesh", methods=["POST"])
def add_mesh():
    data = request.json
    scene["updated_mesh"] = {
        "mesh": data["mesh"],
        "label": data.get("label", "updated")
    }
    return "Updated mesh set", 200

def find_free_port():
    s = socket.socket()
    s.bind(('', 0))  # Let the OS pick a free port
    port = s.getsockname()[1]
    s.close()
    return port

if __name__ == "__main__":
    import socket
    import contextlib

    def find_free_port():
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    port = find_free_port()
    with open("port.txt", "w") as f:
        f.write(str(port))

    app.run(port=port, debug=False)
