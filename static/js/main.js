import {
    initScene,
    animate,
    visibilityState,
    applyVisibility,
    addGlobalAxes
  } from './scene.js';
  
  import { setupControls } from './controls.js';
  import { fetchSceneData } from './api.js';
  

document.addEventListener('DOMContentLoaded', () => {
  const { scene, camera, renderer } = initScene();
  setupControls(camera, renderer.domElement);
  animate(renderer, scene, camera);
  addGlobalAxes(scene);
  fetchSceneData(scene);

  // Hook up toggles — these MUST match the checkbox IDs in viewer.html
  document.getElementById('togglePointCloud').addEventListener('change', e => {
    visibilityState.pointCloud = e.target.checked;
    applyVisibility();
  });

  document.getElementById('toggleFrustums').addEventListener('change', e => {
    visibilityState.frustums = e.target.checked;
    applyVisibility();
  });

  document.getElementById('toggleAxes').addEventListener('change', e => {
    visibilityState.axes = e.target.checked;
    applyVisibility();
  });

  document.getElementById('toggleGlobalAxes').addEventListener('change', e => {
    visibilityState.globalAxes = e.target.checked;
    applyVisibility();
  });
  
  document.getElementById('toggleInitialMesh').addEventListener('change', e => {
    visibilityState.initialMesh = e.target.checked;
    applyVisibility();
  });

  document.getElementById('toggleUpdatedMesh').addEventListener('change', e => {
    visibilityState.updatedMesh = e.target.checked;
    applyVisibility();
  });
});
