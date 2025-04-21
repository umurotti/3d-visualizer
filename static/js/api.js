import {
  setInitialPointCloud,
  setUpdatedPointCloud,
  updateFrustums,
  updateAxes,
  setInitialMesh,
  setUpdatedMesh,
  addGlobalAxes,
  objectGroups // Import objectGroups
} from './scene.js';

import { applyVisibility } from './scene.js';
import { updatePointCloudLabel, updateMeshLabel } from './utils.js';

export function fetchSceneData(scene) {
  fetch('/scene')
    .then(res => res.json())
    .then(data => {
      // Handle frustums
      updateFrustums(scene, data.frustums || []);

      // Handle axes
      updateAxes(scene, data.axes || []);

      // Handle initial mesh
      if (data.initial_mesh) {
        setInitialMesh(scene, data.initial_mesh.mesh);
      } else if (objectGroups.initialMesh) {
        scene.remove(objectGroups.initialMesh);
        objectGroups.initialMesh.geometry.dispose();
        objectGroups.initialMesh.material.dispose();
        objectGroups.initialMesh = null;
      }

      // Handle updated mesh
      if (data.updated_mesh) {
        setUpdatedMesh(scene, data.updated_mesh.mesh, data.updated_mesh.label || "Updated Mesh");
      } else if (objectGroups.updatedMesh) {
        scene.remove(objectGroups.updatedMesh);
        objectGroups.updatedMesh.geometry.dispose();
        objectGroups.updatedMesh.material.dispose();
        objectGroups.updatedMesh = null;
        updateMeshLabel("None"); // Reset the mesh label
      }

      // Handle initial point cloud
      if (data.initial_point_cloud) {
        setInitialPointCloud(scene, data.initial_point_cloud.points);
      } else if (objectGroups.initialPointCloud) {
        scene.remove(objectGroups.initialPointCloud);
        objectGroups.initialPointCloud.geometry.dispose();
        objectGroups.initialPointCloud.material.dispose();
        objectGroups.initialPointCloud = null;
      }

      // Handle updated point cloud
      if (data.updated_point_cloud) {
        setUpdatedPointCloud(scene, data.updated_point_cloud.points, data.updated_point_cloud.label || "Updated Point Cloud");
      } else if (objectGroups.updatedPointCloud) {
        scene.remove(objectGroups.updatedPointCloud);
        objectGroups.updatedPointCloud.geometry.dispose();
        objectGroups.updatedPointCloud.material.dispose();
        objectGroups.updatedPointCloud = null;
        updatePointCloudLabel("None"); // Reset the point cloud label
      }

      // Handle global axes
      if (data.add_global_axes) {
        addGlobalAxes(scene, true);
      }

      applyVisibility(); // Re-apply visibility toggles
    })
    .catch(console.warn);

  setTimeout(() => fetchSceneData(scene), 1000); // Continue polling
}