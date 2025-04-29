import {
  updateFrustums,
  updateAxes,
  addPointCloudToScene,
  addMeshToScene,
  addGlobalAxes
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
      // Handle frustums
      updateFrustums(scene, data.frustums || [], step);

      // Handle axes
      updateAxes(scene, data.axes || []);

      updateSliderMax(data.total_steps); // Update the slider max value

      // Handle updated mesh
      if (data.meshes && data.meshes.length > 0) {
        addMeshToScene(scene, data.meshes[0].mesh, data.meshes[0].color);
      }

      // Handle updated point cloud
      if (data.point_clouds && data.point_clouds.length > 0) {
        addPointCloudToScene(scene, data.point_clouds[0].points, data.point_clouds[0].color);
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