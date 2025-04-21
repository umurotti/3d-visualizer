from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Shared scene state
scene = {
    "initial_point_cloud": None,
    "updated_point_cloud": None,
    "frustums": [],
    "axes": [],
    "initial_mesh": None,           # Only used for the initial mesh
    "updated_mesh": None,   # Last updated mesh (will replace the previous)
    "add_global_axes": False
}

@app.route("/")
def index():
    return render_template("viewer.html")  # Loads modular viewer (main.js)

@app.route("/load_scene", methods=["POST"])
def load_scene():
    data = request.json
    scene["initial_point_cloud"] = {
                                    "points": data.get("points", []),
                                    "label": "initial"
                                    }
    scene["initial_mesh"] = {
                            "mesh": data.get("mesh", []),
                            "label": "initial"
                            }
        
    scene["add_global_axes"] = True

    return "Scene loaded", 200

@app.route("/scene", methods=["GET"])
def get_scene():
    return jsonify({
        "initial_point_cloud": scene["initial_point_cloud"],
        "updated_point_cloud": scene["updated_point_cloud"],
        "frustums": scene["frustums"],
        "axes": scene["axes"],
        "initial_mesh": scene["initial_mesh"],
        "updated_mesh": scene["updated_mesh"],
        "add_global_axes": scene["add_global_axes"]
    })

@app.route("/update_mesh", methods=["POST"])
def update_mesh():
    data = request.json
    scene["updated_mesh"] = {
        "mesh": data["mesh"],
        "label": data.get("label", "updated")
    }
    return "Updated mesh set", 200

@app.route("/update_point_cloud", methods=["POST"])
def update_point_cloud():
    data = request.json
    scene["updated_point_cloud"] = {
        "points": data["points"],
        "label": data.get("label", "updated")
    }
    return "Updated point cloud set", 200

@app.route("/add_frustum", methods=["POST"])
def add_frustum():
    data = request.json
    pose = data["pose"]
    intrinsic = data["intrinsic"]
    width = data["width"]
    height = data["height"]
    near = data["near"]
    far = data["far"]
    color = data["color"]
    visualize_orientation = data["visualize_orientation"]
    scene["frustums"].append({
        "pose": pose,
        "intrinsics": intrinsic,
        "width": width,
        "height": height,
        "near": near,
        "far": far,
        "color": color,
        "visualize_orientation": visualize_orientation,
        })
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

@app.route("/clear_scene", methods=["POST"])
def clear_scene():
    scene["initial_point_cloud"] = None
    scene["updated_point_cloud"] = None
    scene["frustums"] = []
    scene["axes"] = []
    scene["initial_mesh"] = None
    scene["updated_mesh"] = None
    scene["add_global_axes"] = False

    # Reset labels
    scene["updated_point_cloud_label"] = "None"
    scene["updated_mesh_label"] = "None"

    return "Scene cleared", 200

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(debug=False)