import { createAxisLabel, updateLabelBar, updatePointCloudLabel, updateMeshLabel } from './utils.js';
import * as THREE from '/static/vendor/three/build/three.module.js';

export const objectGroups = {
  initialPointCloud: null,
  updatedPointCloud: null,
  frustums: [],
  axes: [],
  globalAxes: [],
  initialMesh: null,
  updatedMesh: null
};

export const visibilityState = {
  initialPointCloud: true,
  updatedPointCloud: true,
  frustums: true,
  axes: true,
  globalAxes: true,
  initialMesh: true,
  updatedMesh: true
};

export function applyVisibility() {
  if (objectGroups.initialPointCloud) objectGroups.initialPointCloud.visible = visibilityState.initialPointCloud;
  if (objectGroups.updatedPointCloud) objectGroups.updatedPointCloud.visible = visibilityState.updatedPointCloud;
  objectGroups.frustums.forEach(f => f.visible = visibilityState.frustums);
  objectGroups.axes.forEach(a => a.visible = visibilityState.axes);
  objectGroups.globalAxes.forEach(a => a.visible = visibilityState.globalAxes);  // ✅

  if (objectGroups.initialMesh) objectGroups.initialMesh.visible = visibilityState.initialMesh;
  if (objectGroups.updatedMesh) objectGroups.updatedMesh.visible = visibilityState.updatedMesh;
}

let light;

export function initScene() {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.01, 100);
  camera.position.set(0, 0, 2);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  document.body.appendChild(renderer.domElement);

  // Directional light that follows the camera
  light = new THREE.DirectionalLight(0xffffff, 1);
  scene.add(light);
  scene.add(light.target); // required for directional light to work

  return { scene, camera, renderer };
}


export function animate(renderer, scene, camera) {
  requestAnimationFrame(() => animate(renderer, scene, camera));
  if (light) {
    light.position.copy(camera.position);
    light.target.position.copy(camera.getWorldDirection(new THREE.Vector3()).add(camera.position));
    light.target.updateMatrixWorld();
  }
  renderer.render(scene, camera);
}

export function setInitialPointCloud(scene, points) {
  if (objectGroups.initialPointCloud) scene.remove(objectGroups.initialPointCloud);

  const pointcloud = createPointCloudFromData(points, 0x888888);
  scene.add(pointcloud);
  objectGroups.initialPointCloud = pointcloud;
}

export function setUpdatedPointCloud(scene, points, label = "Updated Point Cloud") {
  if (objectGroups.updatedPointCloud) {
    scene.remove(objectGroups.updatedPointCloud);
    objectGroups.updatedPointCloud.geometry.dispose();
    objectGroups.updatedPointCloud.material.dispose();
  }

  const pointcloud = createPointCloudFromData(points, 0x00ff00);
  scene.add(pointcloud);
  objectGroups.updatedPointCloud = pointcloud;

  // Update the point cloud label
  updatePointCloudLabel(label);
}

function createPointCloudFromData(entry, color) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(entry.flat()), 3));
  const material = new THREE.PointsMaterial({ color, size: 0.02 });
  return new THREE.Points(geometry, material);
}


export function setInitialMesh(scene, meshData) {
  if (objectGroups.initialMesh) scene.remove(objectGroups.initialMesh);

  const mesh = createMeshFromData(meshData, 0x888888);
  scene.add(mesh);
  objectGroups.initialMesh = mesh;
}

export function setUpdatedMesh(scene, meshData, label = "Updated Mesh") {
  if (objectGroups.updatedMesh) {
    scene.remove(objectGroups.updatedMesh);
    objectGroups.updatedMesh.geometry.dispose();
    objectGroups.updatedMesh.material.dispose();
  }

  const mesh = createMeshFromData(meshData, 0x00ff00);
  scene.add(mesh);
  objectGroups.updatedMesh = mesh;

  // Update the mesh label
  updateMeshLabel(label);
}

function createMeshFromData(entry, color) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(entry.vertices.flat()), 3));
  geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(entry.faces.flat()), 1));
  geometry.computeVertexNormals();

  const material = new THREE.MeshStandardMaterial({
    color,
    metalness: 0.1,
    roughness: 0.8,
    opacity: 0.5,
    transparent: true,
    side: THREE.DoubleSide
  });

  return new THREE.Mesh(geometry, material);
}

export function updateFrustums(scene, frustums) {
  objectGroups.frustums.forEach(obj => scene.remove(obj));
  objectGroups.frustums = [];

  frustums.forEach(entry => {
    const pose = entry.pose;
    const color = entry.color || "#00ff00";

    const geometry = new THREE.ConeGeometry(0.05, 0.1, 8);
    geometry.rotateX(-Math.PI / 2);
    geometry.translate(0, 0, 0.05);

    const material = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.5
    });
    const cone = new THREE.Mesh(geometry, material);

    const m = pose.flat();
    const rot = new THREE.Matrix4().set(
      m[0], m[1], m[2], 0,
      m[4], m[5], m[6], 0,
      m[8], m[9], m[10], 0,
      0,    0,    0,    1
    );
    const pos = new THREE.Vector3(m[3], m[7], m[11]);

    cone.setRotationFromMatrix(rot);
    cone.position.copy(pos);
    scene.add(cone);
    objectGroups.frustums.push(cone);
  });
}

export function updateAxes(scene, axes) {
  objectGroups.axes.forEach(obj => scene.remove(obj));
  objectGroups.axes = [];

  axes.forEach(({ pose, label }) => {
    const m = pose.flat();
    const rot = new THREE.Matrix4().set(m[0], m[1], m[2], 0, m[4], m[5], m[6], 0, m[8], m[9], m[10], 0, 0, 0, 0, 1);
    const pos = new THREE.Vector3(m[3], m[7], m[11]);

    const helper = new THREE.AxesHelper(0.2);
    helper.position.copy(pos);
    helper.setRotationFromMatrix(rot);
    scene.add(helper);

    const labelSprite = createAxisLabel(label);
    labelSprite.position.copy(pos.clone().add(new THREE.Vector3(0, 0.4, 0))); // Adjusted position to avoid clipping
    scene.add(labelSprite);

    objectGroups.axes.push(helper, labelSprite);
  });
}

let globalAxesDrawn = false;

export function addGlobalAxes(scene, force = false) {
  if (globalAxesDrawn && !force) return;

  objectGroups.globalAxes.forEach(obj => scene.remove(obj));
  objectGroups.globalAxes = [];

  const origin = new THREE.Vector3(0, 0, 0);
  const identity = new THREE.Matrix4();
  const helper = new THREE.AxesHelper(0.5);
  helper.position.copy(origin);
  helper.setRotationFromMatrix(identity);
  scene.add(helper);

  const labelSprite = createAxisLabel("Global Axes");
  labelSprite.position.copy(origin.clone().add(new THREE.Vector3(0, 0.6, 0)));
  scene.add(labelSprite);

  objectGroups.globalAxes.push(helper, labelSprite);
  globalAxesDrawn = true;
}