import {
  updateFrustums,
  updateAxes,
  addPointCloudsToScene, // <-- update import
  addMeshToScene,
  addGlobalAxes,
  objectGroups
} from './scene.js';

import { currentSliderValue, updateSliderMax} from './main.js';

import { applyVisibility } from './scene.js';
import { updateStepInput } from './utils.js';

export function fetchSceneData(scene) {
  // Now you can access the latest slider value anytime
  const step = currentSliderValue;
  let url = '/scene';
  if (step !== null) {
    url += `?step=${step}`;
  }
  fetch(url)
    .then(res => res.json())
    .then(data => {
      updateSliderMax(data.total_steps); // Update the slider max value
      // Handle frustums
      updateFrustums(scene, data.frustums || [], step);

      // Handle axes
      updateAxes(scene, data.axes || [], step);

      // Handle updated mesh
      if (data.meshes && data.meshes.length > 0) {
        addMeshToScene(scene, data.meshes[0].mesh, data.meshes[0].color);
      }

      // Handle updated point clouds
      if (data.point_clouds && data.point_clouds.length > 0) {
        addPointCloudsToScene(scene, data.point_clouds);
      } else {
        // Clear the point cloud if none for this step
        if (objectGroups.updatedPointCloud) {
          if (Array.isArray(objectGroups.updatedPointCloud)) {
            objectGroups.updatedPointCloud.forEach(pc => {
              scene.remove(pc);
              pc.geometry.dispose();
              pc.material.dispose();
            });
          } else {
            scene.remove(objectGroups.updatedPointCloud);
            objectGroups.updatedPointCloud.geometry.dispose();
            objectGroups.updatedPointCloud.material.dispose();
          }
          objectGroups.updatedPointCloud = null;
        }
      }

      // Handle global axes
      if (data.add_global_axes) {
        addGlobalAxes(scene, true);
      }
      updateStepInput(step);
      applyVisibility(); // Re-apply visibility toggles
    })
    .catch(console.warn);

  setTimeout(() => fetchSceneData(scene), 1000); // Continue polling
}