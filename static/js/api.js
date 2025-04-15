import {
  updatePointCloud,
  updateFrustums,
  updateAxes,
  setInitialMesh,
  setUpdatedMesh,
  addGlobalAxes
} from './scene.js';

import { applyVisibility } from './scene.js';

export function fetchSceneData(scene) {
  fetch('/scene')
    .then(res => res.json())
    .then(data => {
      updatePointCloud(scene, data.points);
      updateFrustums(scene, data.frustums);
      updateAxes(scene, data.axes);
      if (data.meshes?.length > 0) setInitialMesh(scene, data.meshes[0].mesh);
      if (data.updated_mesh) setUpdatedMesh(scene, data.updated_mesh.mesh);

      // ✅ Only call if the backend says it's needed
      if (data.add_global_axes) addGlobalAxes(scene, true);

      applyVisibility();  // re-apply toggle settings
    })
    .catch(console.warn);

  setTimeout(() => fetchSceneData(scene), 1000);
}