import json
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Shared scene state
scene = {
    "point_clouds": [],           # Only used for the initial point clou
    "frustums": [],
    "axes": [],
    "meshes": [],
    "add_global_axes": False,
    "total_steps": 0
}

@app.route("/")
def index():
    return render_template("viewer.html")  # Loads modular viewer (main.js)

@app.route("/save_scene", methods=["POST"])
def save_scene():
    data = request.json
    save_path = data.get("save_path", "saved_scene.json")  # default fallback

    try:
        with open(save_path, "w") as f:
            json.dump(scene, f)
        return f"Scene saved to {save_path}", 200
    except Exception as e:
        return f"Error saving scene: {str(e)}", 500

@app.route("/load_scene", methods=["POST"])
def load_scene():
    data = request.json
    load_path = data.get("load_path", "saved_scene.json")  # default fallback

    if not os.path.exists(load_path):
        return f"No scene found at {load_path}", 404

    try:
        with open(load_path, "r") as f:
            saved_scene = json.load(f)
            scene.update(saved_scene)
        return f"Scene loaded from {load_path}", 200
    except Exception as e:
        return f"Error loading scene: {str(e)}", 500

def get_max_step():
    max_step = 0
    for key in ["point_clouds", "frustums", "axes", "meshes"]:
        for obj in scene.get(key, []):
            if isinstance(obj, dict) and "step" in obj:
                max_step = max(max_step, obj["step"])
    return max_step

@app.route("/scene", methods=["GET"])
def get_scene():
    step = request.args.get('step', default=None, type=int)
    total_steps = get_max_step()
    if step is not None:
        return jsonify({
            "point_clouds": [pc for pc in scene["point_clouds"] if pc.get("step") == step],
            "frustums": [f for f in scene["frustums"] if f.get("step") == step],
            "axes": [a for a in scene["axes"] if a.get("step") == step],
            "meshes": [m for m in scene["meshes"] if m.get("step") == step],
            "add_global_axes": scene["add_global_axes"],
            "total_steps": total_steps
        })
    else:
        return jsonify({
            "point_clouds": scene["point_clouds"],
            "frustums": scene["frustums"],
            "axes": scene["axes"],
            "meshes": scene["meshes"],
            "add_global_axes": scene["add_global_axes"],
            "total_steps": total_steps
        })

@app.route("/add_mesh", methods=["POST"])
def add_mesh():
    data = request.json
    scene["meshes"].append({
        "mesh": data["mesh"],
        "color": data["color"],
        "step": data["step"]
    })
    return "Updated mesh set", 200

@app.route("/add_point_cloud", methods=["POST"])
def add_point_cloud():
    data = request.json
    scene["point_clouds"].append({
        "points": data["points"],
        "color": data["color"],
        "step": data["step"]
    })
    return "Updated point cloud set", 200

@app.route("/add_frustum", methods=["POST"])
def add_frustum():
    data = request.json
    
    scene["frustums"].append({
        "pose":                     data["pose"],
        "intrinsics":               data["intrinsic"],
        "width":                    data["width"],
        "height":                   data["height"],
        "near":                     data["near"],
        "far":                      data["far"],
        "color":                    data["color"],
        "visualize_orientation":    data["visualize_orientation"],
        "step":                     data["step"]
        })
    return "Frustum added", 200

@app.route("/add_object_axis", methods=["POST"])
def add_object_axis():
    data = request.json
    scene["axes"].append({
        "pose": data["pose"],
        "step": data["step"]
    })
    return "Object axis added", 200

@app.route("/add_global_axes", methods=["POST"])
def add_global_axes():
    scene["add_global_axes"] = True
    return "Global axes flag set", 200

@app.route("/clear_scene", methods=["POST"])
def clear_scene():
    scene["point_clouds"] = []
    scene["frustums"] = []
    scene["axes"] = []
    scene["meshes"] = []
    scene["add_global_axes"] = False

    return "Scene cleared", 200

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(debug=False)