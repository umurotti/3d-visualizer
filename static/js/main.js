import {
    initScene,
    animate,
    visibilityState,
    applyVisibility,
    addGlobalAxes
  } from './scene.js';
  
  import { setupControls } from './controls.js';
  import { fetchSceneData, startScenePolling, stopScenePolling } from './api.js';
  

document.addEventListener('DOMContentLoaded', () => {
  const { scene, camera, renderer } = initScene();
  setupRecording(scene, renderer);
  setupControls(camera, renderer.domElement);
  animate(renderer, scene, camera);
  addGlobalAxes(scene);
  startScenePolling(scene);

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

  const gridToggle = document.getElementById('toggleGrid');
  if (gridToggle) {
    gridToggle.addEventListener('change', e => {
      visibilityState.grid = e.target.checked;
      applyVisibility();
    });
  }
});

// Export slider value and update function
export let currentSliderValue = 0;
let isRecording = false;
let recorder;
let recordedChunks = [];
let recordingResolve = null;
let queuedFrames = [];
let recordingFps = 10;

function getSupportedMimeType() {
  const candidates = [
    'video/webm;codecs=vp9',
    'video/webm;codecs=vp8',
    'video/webm;codecs=avc1',
    'video/webm'
  ];
  for (const type of candidates) {
    if (!type || (window.MediaRecorder && MediaRecorder.isTypeSupported(type))) {
      return type;
    }
  }
  return '';
}

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

async function playFrameQueue(scene, renderer, canvas) {
  if (isRecording || queuedFrames.length === 0) {
    return;
  }
  stopScenePolling();
  isRecording = true;
  const stream = canvas.captureStream(recordingFps);
  recordedChunks = [];

  const mimeType = getSupportedMimeType();
  if (!mimeType) {
    console.warn('MediaRecorder: unable to find a supported WebM mime type.');
    isRecording = false;
    stream.getTracks().forEach(track => track.stop());
    startScenePolling(scene);
    return;
  }
  recorder = new MediaRecorder(stream, { mimeType });
  recorder.ondataavailable = event => {
    if (event.data && event.data.size > 0) {
      recordedChunks.push(event.data);
    }
  };
  recorder.onstop = () => {
    const blob = new Blob(recordedChunks, { type: 'video/webm' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = 'reconstruction.webm';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }, 100);
    isRecording = false;
    startScenePolling(scene);
    if (recordingResolve) {
      recordingResolve();
      recordingResolve = null;
    }
  };
  recorder.start();

  for (const frame of queuedFrames) {
    timeSlider.value = frame;
    currentSliderValue = frame;
    stepInput.value = frame;
    await fetchSceneData(scene, { scheduleNext: false });
    await new Promise(resolve => setTimeout(resolve, 1000 / recordingFps));
  }

  recorder.stop();
  queuedFrames = [];
}

function startRecording(scene, renderer, canvas) {
  if (isRecording) {
    console.warn('Recording already in progress.');
    return;
  }
  const total = parseInt(timeSlider.max);
  if (!Number.isFinite(total) || total <= 0) {
    console.warn('No frames to record.');
    return;
  }
  queuedFrames = [];
  for (let i = 0; i <= total; ++i) {
    queuedFrames.push(i);
  }
  queuedFrames.sort((a, b) => a - b);
  playFrameQueue(scene, renderer, canvas);
}

function setupRecording(scene, renderer) {
  const canvas = renderer.domElement;
  const recordBtn = document.getElementById('recordVideo');
  if (!recordBtn) return;
  recordBtn.addEventListener('click', () => startRecording(scene, renderer, canvas));
}
