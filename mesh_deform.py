import time
import numpy as np
import trimesh
from viewer_client import Online3DViewer
from sklearn.neighbors import NearestNeighbors
import asyncio

# === Helper Functions ===
def normalize(v):
    return v / np.linalg.norm(v)

def look_at(camera_position, target_position, up=np.array([0, 1, 0])):
    forward = normalize(target_position - camera_position)
    right = normalize(np.cross(up, forward))
    true_up = np.cross(forward, right)

    pose = np.eye(4)
    pose[:3, :3] = np.stack([right, true_up, forward], axis=1)
    pose[:3, 3] = camera_position
    return pose

def match_vertex_count(source, target):
    """Downsample or upsample source to match target vertices count."""
    n_target = len(target.vertices)
    if len(source.vertices) == n_target:
        return source
    elif len(source.vertices) > n_target:
        # Downsample
        idx = np.random.choice(len(source.vertices), n_target, replace=False)
        return trimesh.Trimesh(vertices=source.vertices[idx], faces=[])
    else:
        # Upsample using Nearest Neighbors interpolation
        nn = NearestNeighbors(n_neighbors=1).fit(source.vertices)
        idx = np.random.choice(len(source.vertices), n_target, replace=True)
        new_vertices = source.vertices[idx]
        return trimesh.Trimesh(vertices=new_vertices, faces=[])

# === Load target mesh (Stanford Bunny) ===
bunny_path = "demo/bunny/reconstruction/bun_zipper_res3.ply"
bunny = trimesh.load(bunny_path)
bunny.apply_translation(-bunny.bounding_box.centroid)

# === Create initial mesh (sphere) ===
sphere = trimesh.creation.icosphere(subdivisions=4, radius=0.2)
sphere.apply_translation(-sphere.bounding_box.centroid)

# === Match vertex count ===
sphere = match_vertex_count(sphere, bunny)

# === Prepare viewer ===
viewer = Online3DViewer()
viewer.clear_scene()
viewer.load_scene(mesh=sphere)
viewer.add_global_axes()

# === Setup camera ===
initial_center = np.zeros(3)
cam_pose = look_at(np.array([1.0, 1.0, 1.0]), initial_center)
viewer.add_frustum(cam_pose, color="#ff0000")

# === Morphing steps ===
import time

start = time.time()

steps = 1000
tasks = []
for i in range(steps + 1):
    alpha = i / steps
    interpolated_vertices = (1 - alpha) * sphere.vertices + alpha * bunny.vertices
    interpolated_mesh = trimesh.Trimesh(vertices=interpolated_vertices, faces=bunny.faces)

    # Prepare async mesh update
    tasks.append(viewer.async_add_mesh(interpolated_mesh, label=f"step_{i}"))

end = time.time()

print(f"Elapsed time: {end - start:.6f} seconds")
print("Deformation demo complete.")

# Run all updates concurrently using an async function
async def main():
    await asyncio.gather(*tasks)
    
asyncio.run(main())