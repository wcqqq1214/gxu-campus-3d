import {
  BufferAttribute,
  BufferGeometry,
  Color,
  Mesh,
  MeshStandardMaterial,
  Points,
  ShaderMaterial,
  Vector3,
  type Object3D,
} from 'three';

/** Connected panes (or continuous glass floors) share one deterministic light. */
export function windowLights(
  geometry: BufferGeometry,
  matrix: Mesh['matrixWorld'],
) {
  const position = geometry.getAttribute('position');
  const count = position.count;
  const parent = Int32Array.from({ length: count }, (_, i) => i);
  function find(i: number): number {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]];
      i = parent[i];
    }
    return i;
  }
  const index = geometry.index;
  for (let i = 0; i < (index?.count ?? count); i += 3) {
    const a = index ? index.getX(i) : i;
    for (let k = 1; k < 3; k++)
      parent[find(index ? index.getX(i + k) : i + k)] = find(a);
  }
  // Separate triangles without an index can still share corners in the same pane.
  const corners = new Map<string, number>();
  for (let i = 0; i < count; i++) {
    const key = `${position.getX(i).toFixed(3)},${position.getY(i).toFixed(3)},${position.getZ(i).toFixed(3)}`;
    const first = corners.get(key);
    if (first !== undefined) parent[find(i)] = find(first);
    else corners.set(key, i);
  }
  const centers = new Map<number, { sum: Vector3; count: number }>();
  const point = new Vector3();
  for (let i = 0; i < count; i++) {
    const root = find(i);
    if (!centers.has(root)) centers.set(root, { sum: new Vector3(), count: 0 });
    const center = centers.get(root)!;
    center.sum.add(point.fromBufferAttribute(position, i));
    center.count++;
  }
  const lights = new Map<number, number>();
  for (const [root, center] of centers) {
    point.copy(center.sum).divideScalar(center.count).applyMatrix4(matrix);
    const key = point
      .toArray()
      .map((v) => Math.round(v * 10))
      .join(',');
    let hash = 2166136261;
    for (const c of key)
      hash = Math.imul(hash ^ c.charCodeAt(0), 16777619) >>> 0;
    lights.set(
      root,
      hash / 4294967296 < 0.47 ? 0.78 + ((hash >>> 8) % 23) / 100 : 0,
    );
  }
  return Float32Array.from({ length: count }, (_, i) => lights.get(find(i))!);
}

export function createNightStyle() {
  const prepared = new WeakSet<MeshStandardMaterial>();
  const albedos = new WeakMap<MeshStandardMaterial, Color>();
  return {
    copyDayColor(source: MeshStandardMaterial, target: MeshStandardMaterial) {
      target.color.copy(albedos.get(source) ?? source.color);
    },
    apply(mesh: Mesh, night: boolean) {
      for (const material of Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material]) {
        if (!(material instanceof MeshStandardMaterial)) continue;
        if (
          ['grass', 'green', 'road', 'asphalt', 'path', 'treeCanopy'].includes(
            material.name,
          )
        ) {
          if (!albedos.has(material))
            albedos.set(material, material.color.clone());
          material.color
            .copy(albedos.get(material)!)
            .multiplyScalar(night ? 0.6 : 1);
        }
        if (material.name === 'lampGlass') {
          material.emissive.set('#fff0d0');
          material.emissiveIntensity = night ? 3.5 : 0;
          continue;
        }
        if (!/glass$/i.test(material.name) || material.name === 'courtGlass')
          continue;
        if (night && !mesh.geometry.hasAttribute('windowLight')) {
          mesh.updateWorldMatrix(true, false);
          mesh.geometry.setAttribute(
            'windowLight',
            new BufferAttribute(
              windowLights(mesh.geometry, mesh.matrixWorld),
              1,
            ),
          );
        }
        if (!prepared.has(material)) {
          prepared.add(material);
          material.onBeforeCompile = (shader) => {
            if (!material.defines?.CAMPUS_NIGHT_WINDOWS) return;
            shader.vertexShader =
              'attribute float windowLight; varying float vWindowLight;\n' +
              shader.vertexShader;
            shader.vertexShader = shader.vertexShader.replace(
              '#include <begin_vertex>',
              '#include <begin_vertex>\nvWindowLight = windowLight;',
            );
            shader.fragmentShader =
              'varying float vWindowLight;\n' + shader.fragmentShader;
            shader.fragmentShader = shader.fragmentShader.replace(
              '#include <emissivemap_fragment>',
              '#include <emissivemap_fragment>\ntotalEmissiveRadiance *= vWindowLight;',
            );
          };
          material.customProgramCacheKey = () => 'campus-window-light-v1';
        }
        const enabled = material.defines?.CAMPUS_NIGHT_WINDOWS === 1;
        if (enabled !== night) {
          material.defines = {
            ...material.defines,
            CAMPUS_NIGHT_WINDOWS: night ? 1 : 0,
          };
          material.needsUpdate = true;
        }
        material.emissive.set('#ffe2b5');
        material.emissiveIntensity = night ? 1.5 : 0;
      }
    },
  };
}

/** Schematic road-edge lamps follow existing curb vertices, never add real lights. */
export function createRoadLights(root: Object3D) {
  root.updateMatrixWorld(true);
  const cells = new Map<string, Vector3>();
  const point = new Vector3();
  root.traverse((o) => {
    if (
      !(o instanceof Mesh) ||
      !(o.material instanceof MeshStandardMaterial) ||
      o.material.name !== 'curb'
    )
      return;
    const positions = o.geometry.getAttribute('position');
    for (let i = 0; i < positions.count; i++) {
      point.fromBufferAttribute(positions, i).applyMatrix4(o.matrixWorld);
      const key = `${Math.floor(point.x / 42)},${Math.floor(point.z / 42)}`;
      if (!cells.has(key))
        cells.set(key, point.clone().add(new Vector3(0, 5.8, 0)));
    }
  });
  const geometry = new BufferGeometry();
  geometry.setAttribute(
    'position',
    new BufferAttribute(
      new Float32Array([...cells.values()].flatMap((p) => p.toArray())),
      3,
    ),
  );
  const material = new ShaderMaterial({
    uniforms: {
      lampColor: { value: new Color('#ffdfad').multiplyScalar(3.5) },
      pixelRatio: { value: 1 },
    },
    vertexShader: `uniform float pixelRatio;
      void main() { vec4 p = modelViewMatrix * vec4(position,1.0); gl_Position = projectionMatrix * p;
        gl_PointSize = clamp(1600.0 / max(1.0, -p.z), 1.4, 5.0) * pixelRatio; }`,
    fragmentShader: `uniform vec3 lampColor;
      void main() { float radius = length(gl_PointCoord - 0.5);
        float alpha = 1.0 - smoothstep(0.12,0.5,radius); if(alpha<0.02) discard;
        gl_FragColor = vec4(lampColor,alpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    transparent: true,
    depthWrite: false,
  });
  const lights = new Points(geometry, material);
  lights.name = 'road-night-lights';
  return lights;
}
