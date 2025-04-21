import * as THREE from '/static/vendor/three/build/three.module.js';


export function createAxisLabel(text, color = 'white') {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = color;
    ctx.font = 'bold 48px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, canvas.width / 2, canvas.height / 2);
  
    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(0.4, 0.2, 1.0);
    return sprite;
  }

export function updateLabelBar(text) {
  const labelBar = document.getElementById('label-bar');
  if (labelBar) {
    labelBar.textContent = `Currently showing: ${text}`;
  }
}

export function updatePointCloudLabel(text) {
  const pointCloudLabel = document.getElementById('pointcloud-label');
  if (pointCloudLabel) {
    pointCloudLabel.textContent = `Point Cloud: ${text}`;
  }
}

export function updateMeshLabel(text) {
  const meshLabel = document.getElementById('mesh-label');
  if (meshLabel) {
    meshLabel.textContent = `Mesh: ${text}`;
  }
}
