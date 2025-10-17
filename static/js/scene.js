import { createAxisLabel} from './utils.js';
import * as THREE from '/static/vendor/three/build/three.module.js';

export const objectGroups = {
  initialPointCloud: null,
  updatedPointCloud: null,
  frustums: [],
  axes: [],
  globalAxes: [],
  initialMesh: null,
  updatedMesh: null,
  meshLabels: [],
  cameraHelpers: []
};

export const visibilityState = {
  initialPointCloud: true,
  updatedPointCloud: true,
  frustums: true,
  axes: true,
  globalAxes: true,
  initialMesh: true,
  updatedMesh: true,
  grid: true
};

export function applyVisibility() {
  if (objectGroups.initialPointCloud) {
    objectGroups.initialPointCloud.visible = visibilityState.initialPointCloud;
  }
  if (Array.isArray(objectGroups.updatedPointCloud)) {
    objectGroups.updatedPointCloud.forEach(pc => {
      if (pc) pc.visible = visibilityState.updatedPointCloud;
    });
  } else if (objectGroups.updatedPointCloud) {
    objectGroups.updatedPointCloud.visible = visibilityState.updatedPointCloud;
  }
  objectGroups.frustums.forEach(f => f.visible = visibilityState.frustums);
  objectGroups.axes.forEach(a => a.visible = visibilityState.axes);
  objectGroups.globalAxes.forEach(a => a.visible = visibilityState.globalAxes);  // ✅

  if (objectGroups.initialMesh) objectGroups.initialMesh.visible = visibilityState.initialMesh;
  if (Array.isArray(objectGroups.updatedMesh)) {
    objectGroups.updatedMesh.forEach(mesh => {
      if (mesh) mesh.visible = visibilityState.updatedMesh;
    });
  } else if (objectGroups.updatedMesh) {
    objectGroups.updatedMesh.visible = visibilityState.updatedMesh;
  }
  if (Array.isArray(objectGroups.meshLabels)) {
    objectGroups.meshLabels.forEach(label => {
      if (label) label.visible = visibilityState.updatedMesh;
    });
  }
  if (objectGroups.gridHelper) {
    objectGroups.gridHelper.visible = visibilityState.grid;
  }
}

let light;

function disposeObject3D(object) {
  if (!object) return;
  object.traverse(child => {
    if (child.geometry) {
      child.geometry.dispose();
    }
    if (child.material) {
      if (Array.isArray(child.material)) {
        child.material.forEach(mat => mat && mat.dispose());
      } else {
        child.material.dispose();
      }
    }
  });
}

export function initScene() {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.01, 100);
  camera.position.set(0, 0, 2);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0xffffff, 1);
  scene.background = new THREE.Color(0xffffff);
  document.body.appendChild(renderer.domElement);

  const gridHelper = new THREE.GridHelper(2.5, 25, 0xd0d0d0, 0xe5e5e5);
  gridHelper.position.y = -0.001;
  scene.add(gridHelper);
  objectGroups.gridHelper = gridHelper;

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

export function addPointCloudToScene(scene, points, color) {
  if (objectGroups.updatedPointCloud) {
    disposeObject3D(objectGroups.updatedPointCloud);
    scene.remove(objectGroups.updatedPointCloud);
  }

  const pointcloud = createPointCloudFromData(points, color);
  scene.add(pointcloud);
  objectGroups.updatedPointCloud = pointcloud;
}

export function addPointCloudsToScene(scene, pointClouds) {
  // Remove previous point clouds
  if (objectGroups.updatedPointCloud) {
    if (Array.isArray(objectGroups.updatedPointCloud)) {
      objectGroups.updatedPointCloud.forEach(pc => {
        disposeObject3D(pc);
        scene.remove(pc);
      });
    } else {
      disposeObject3D(objectGroups.updatedPointCloud);
      scene.remove(objectGroups.updatedPointCloud);
    }
    objectGroups.updatedPointCloud = null;
  }

  // Add all new point clouds
  objectGroups.updatedPointCloud = [];
  for (const pc of pointClouds) {
    const pointcloud = createPointCloudFromData(pc.points, pc.color);
    scene.add(pointcloud);
    objectGroups.updatedPointCloud.push(pointcloud);
  }
}

function createPointCloudFromData(entry, color) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(entry.flat()), 3));
  const material = new THREE.PointsMaterial({ color, size: 0.02 });
  return new THREE.Points(geometry, material);
}


export function addMeshesToScene(scene, meshes) {
  if (Array.isArray(objectGroups.updatedMesh)) {
    objectGroups.updatedMesh.forEach(mesh => {
      disposeObject3D(mesh);
      scene.remove(mesh);
    });
  } else if (objectGroups.updatedMesh) {
    disposeObject3D(objectGroups.updatedMesh);
    scene.remove(objectGroups.updatedMesh);
  }
  if (Array.isArray(objectGroups.meshLabels)) {
    objectGroups.meshLabels.forEach(label => {
      if (label.parent) {
        label.parent.remove(label);
      }
      disposeObject3D(label);
    });
  }
  objectGroups.meshLabels = [];

  if (!meshes || meshes.length === 0) {
    objectGroups.updatedMesh = null;
    return;
  }

  console.debug(`Rendering ${meshes.length} mesh(es) for current step.`);
  objectGroups.updatedMesh = [];
  for (const entry of meshes) {
    const mesh = createMeshFromData(entry);
    mesh.name = entry.label || `mesh_${objectGroups.updatedMesh.length}`;
    scene.add(mesh);
    if (mesh.geometry && !mesh.geometry.boundingBox) {
      mesh.geometry.computeBoundingBox();
      mesh.geometry.computeBoundingSphere();
    }
    const labelText = entry.label || mesh.name;
    if (labelText && mesh.geometry.boundingBox) {
      const center = new THREE.Vector3();
      mesh.geometry.boundingBox.getCenter(center);
      const size = new THREE.Vector3();
      mesh.geometry.boundingBox.getSize(size);
      const labelSprite = createAxisLabel(labelText);
      labelSprite.position.copy(center);
      labelSprite.position.y += size.y / 2 + 0.04;
      mesh.add(labelSprite);
      objectGroups.meshLabels.push(labelSprite);
    }
    console.debug(`Added mesh ${mesh.name}`, mesh.geometry?.boundingBox);
    objectGroups.updatedMesh.push(mesh);
  }
}

function createMeshFromData(entry) {
  const { mesh, color, label } = entry;

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(mesh.vertices.flat()), 3));
  geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(mesh.faces.flat()), 1));
  geometry.computeVertexNormals();

  const colorLower = typeof color === 'string' ? color.toLowerCase() : null;
  const labelLower = typeof label === 'string' ? label.toLowerCase() : null;

  const materialOptions = {
    color,
    metalness: 0.25,
    roughness: 0.65,
    transparent: false,
    side: THREE.DoubleSide,
    depthWrite: true
  };

  const isHand = (labelLower && labelLower.includes('hand')) || (colorLower === '#1f77b4');
  if (isHand) {
    materialOptions.polygonOffset = true;
    materialOptions.polygonOffsetFactor = -1;
    materialOptions.polygonOffsetUnits = -1;
  }

  const material = new THREE.MeshStandardMaterial(materialOptions);
  const meshObject = new THREE.Mesh(geometry, material);
  meshObject.castShadow = false;
  meshObject.receiveShadow = false;

  return meshObject;
}

function createCameraModel(color = 0x1a1a1a) {
  const bodyGeometry = new THREE.BoxGeometry(0.05, 0.035, 0.03);
  const bodyMaterial = new THREE.MeshStandardMaterial({ color, metalness: 0.5, roughness: 0.5 });
  const body = new THREE.Mesh(bodyGeometry, bodyMaterial);

  const lensGeometry = new THREE.CylinderGeometry(0.014, 0.014, 0.032, 24);
  const lensMaterial = new THREE.MeshStandardMaterial({ color: 0x555555, metalness: 0.6, roughness: 0.3 });
  const lens = new THREE.Mesh(lensGeometry, lensMaterial);
  lens.rotation.x = Math.PI / 2;
  lens.position.z = 0.03;

  const group = new THREE.Group();
  group.add(body);
  group.add(lens);
  return group;
}

function getFrustumPointsFromK(K, width, height, near, far) {
  const fx = K[0][0], fy = K[1][1];
  const cx = K[0][2], cy = K[1][2];

  const corners = [
      [0, 0],         // top-left
      [width, 0],     // top-right
      [width, height],// bottom-right
      [0, height],    // bottom-left
  ];

  function pixelToCam(u, v, depth) {
      const x = (u - cx) * depth / fx;
      const y = (v - cy) * depth / fy;
      return new THREE.Vector3(x, y, depth);
  }

  // Compute corners at near and far planes
  const nearPoints = corners.map(([u, v]) => pixelToCam(u, v, near));
  const farPoints = corners.map(([u, v]) => pixelToCam(u, v, far));

  return nearPoints.concat(farPoints);  // 8 points
}

function createFrustumLines(points, color) {
  const indices = [
      // near plane
      [0,1],[1,2],[2,3],[3,0],
      // far plane
      [4,5],[5,6],[6,7],[7,4],
      // sides
      [0,4],[1,5],[2,6],[3,7]
  ];

  const geometry = new THREE.BufferGeometry();
  const vertices = [];

  for (const [i, j] of indices) {
      vertices.push(points[i].x, points[i].y, points[i].z);
      vertices.push(points[j].x, points[j].y, points[j].z);
  }

  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

  const material = new THREE.LineBasicMaterial({ color: color });
  return new THREE.LineSegments(geometry, material);
}

function applyPoseToPoints(points, poseMatrix) {
  return points.map(p => p.clone().applyMatrix4(poseMatrix));
}

function arrayToMatrix4(poseArray) {
  // Flatten the 4x4 nested array into a 1D array (row-major order)
  const flat = poseArray.flat();
  const m = new THREE.Matrix4();
  m.set(...flat);
  return m;
}

function drawCameraAxes(origin, poseMatrix, length = 0.1) {
  const axes = [];

  const directions = {
      x: new THREE.Vector3(length, 0, 0), // right
      y: new THREE.Vector3(0, length, 0), // up
      z: new THREE.Vector3(0, 0, length), // forward
  };

  const colors = {
      x: 0xff0000,
      y: 0x00ff00,
      z: 0x0000ff,
  };

  for (let axis in directions) {
      const dir = directions[axis].clone().applyMatrix4(poseMatrix).sub(origin);
      const arrow = new THREE.ArrowHelper(
          dir.clone().normalize(),
          origin,
          dir.length(),
          colors[axis],
          0.015,
          0.01
      );
      axes.push(arrow);
  }

  return axes;
}


export function updateFrustums(scene, frustums, maxStep = Infinity) {
  objectGroups.frustums.forEach(obj => scene.remove(obj));
  objectGroups.frustums = [];
  if (Array.isArray(objectGroups.cameraHelpers)) {
    objectGroups.cameraHelpers.forEach(obj => scene.remove(obj));
  }
  objectGroups.cameraHelpers = [];

  frustums.forEach(entry => {
    if (entry.step !== undefined && entry.step > maxStep) return;  // <-- SKIP if too big

    const poseMatrix = arrayToMatrix4(entry.pose);
    let frustumPoints = getFrustumPointsFromK(entry.intrinsics, entry.width, entry.height, entry.near, entry.far);
    frustumPoints = applyPoseToPoints(frustumPoints, poseMatrix);
    const frustum = createFrustumLines(frustumPoints, entry.color);
    scene.add(frustum);

    const cameraHelper = createCameraModel();
    const position = new THREE.Vector3();
    const quaternion = new THREE.Quaternion();
    const scale = new THREE.Vector3();
    poseMatrix.decompose(position, quaternion, scale);
    cameraHelper.position.copy(position);
    cameraHelper.quaternion.copy(quaternion);
    cameraHelper.scale.setScalar(0.08);
    scene.add(cameraHelper);
    objectGroups.cameraHelpers.push(cameraHelper);

    if (entry.visualize_orientation) {
      const axes = drawCameraAxes(frustumPoints[0], poseMatrix);
      axes.forEach(axis => scene.add(axis));
      objectGroups.frustums.push(...axes);
    }
    objectGroups.frustums.push(cameraHelper);
    objectGroups.frustums.push(frustum);
  });
}

export function updateAxes(scene, axes, currentStep, maxStep = Infinity) {
  objectGroups.axes.forEach(obj => scene.remove(obj));
  objectGroups.axes = [];

  axes.forEach(({ pose, label, step }) => {
    if (step !== currentStep) return;  // <-- SKIP if not the current step
    if (step !== undefined && step > maxStep) return;  // <-- SKIP if too big

    const m = pose.flat();
    const rot = new THREE.Matrix4().set(m[0], m[1], m[2], 0, m[4], m[5], m[6], 0, m[8], m[9], m[10], 0, 0, 0, 0, 1);
    const pos = new THREE.Vector3(m[3], m[7], m[11]);

    const helper = new THREE.AxesHelper(0.2);
    helper.position.copy(pos);
    helper.setRotationFromMatrix(rot);
    scene.add(helper);

    const labelSprite = createAxisLabel(label);
    labelSprite.position.copy(pos.clone().add(new THREE.Vector3(0, 0.4, 0)));
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