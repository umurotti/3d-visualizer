import {
  updateFrustums,
  updateAxes,
  addPointCloudsToScene, // <-- update import
  addMeshesToScene,
  addGlobalAxes,
  objectGroups
} from './scene.js';

import { currentSliderValue, updateSliderMax} from './main.js';

import { applyVisibility } from './scene.js';
import { updateStepInput } from './utils.js';

let pollingHandle = null;

export function fetchSceneData(scene, { scheduleNext = true } = {}) {
  const step = currentSliderValue;
  let url = '/scene';
  if (step !== null && step !== undefined) {
    url += `?step=${step}`;
  }

  const fetchPromise = fetch(url)
    .then(res => res.json())
    .then(data => {
      updateSliderMax(data.total_steps);
      updateFrustums(scene, data.frustums || [], step);
      updateAxes(scene, data.axes || [], step);

      if (data.meshes && data.meshes.length > 0) {
        addMeshesToScene(scene, data.meshes);
      } else {
        addMeshesToScene(scene, []);
      }

      if (data.point_clouds && data.point_clouds.length > 0) {
        addPointCloudsToScene(scene, data.point_clouds);
      } else {
        addPointCloudsToScene(scene, []);
      }

      if (data.add_global_axes) {
        addGlobalAxes(scene, true);
      }
      updateStepInput(step);
      applyVisibility();
    })
    .catch(err => {
      console.warn(err);
    });

  if (scheduleNext) {
    if (pollingHandle !== null) {
      clearTimeout(pollingHandle);
    }
    pollingHandle = setTimeout(() => fetchSceneData(scene, { scheduleNext: true }), 1000);
  }

  return fetchPromise;
}

export function stopScenePolling() {
  if (pollingHandle !== null) {
    clearTimeout(pollingHandle);
    pollingHandle = null;
  }
}

export function startScenePolling(scene) {
  stopScenePolling();
  fetchSceneData(scene, { scheduleNext: true });
}
