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
    visibilityState.updatedPointCloud = e.target.checked;
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
  
  document.getElementById('toggleMesh').addEventListener('change', e => {
    visibilityState.updatedMesh = e.target.checked;
    applyVisibility();
  });
});

// Export slider value and update function
export let currentSliderValue = 0;
export let globalScene = null;

export function setGlobalScene(scene) {
  globalScene = scene;
}

const timeSlider = document.getElementById('time-slider');
const stepInput = document.getElementById('step-input');
export let isTypingStep = false;

export function updateSliderMax(newMax) {
  timeSlider.max = newMax;
}

timeSlider.addEventListener('input', (event) => {
  currentSliderValue = parseInt(event.target.value, 10);
});

stepInput.addEventListener('focus', () => {
  isTypingStep = true;  // User started typing
});

stepInput.addEventListener('blur', () => {
  isTypingStep = false; // User finished typing
});

stepInput.addEventListener('change', () => {
  let newStep = parseInt(stepInput.value);
  if (!isNaN(newStep)) {
    newStep = Math.max(0, Math.min(newStep, parseInt(timeSlider.max)));
    timeSlider.value = newStep;
    currentSliderValue = newStep;
    stepInput.value = newStep;
  }
});
