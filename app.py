from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

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
    step = request.args.get('step', default=None, type=int)  # Get 'index' from URL
    if step is not None:
        # Return only the specific indexed elements
        return jsonify({
            "point_clouds": [scene["point_clouds"][step]] if scene["point_clouds"] else [],
            "frustums": scene["frustums"],
            "axes": scene["axes"],
            "meshes": [scene["meshes"][step]] if scene["meshes"] else [],
            "add_global_axes": scene["add_global_axes"],
            "total_steps": (len(scene["point_clouds"]) - 1) if scene["point_clouds"] else 0
        })
    else:
        # If no index is provided, return everything
        return jsonify({
            "point_clouds": scene["point_clouds"],
            "frustums": scene["frustums"],
            "axes": scene["axes"],
            "meshes": scene["meshes"],
            "add_global_axes": scene["add_global_axes"],
            "total_steps": scene["total_steps"]
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