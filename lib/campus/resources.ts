import * as THREE from 'three';

function resources(root: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  const textures = new Set<THREE.Texture>();
  const instances = new Set<THREE.InstancedMesh>();
  const shadows = new Set<THREE.LightShadow>();
  root.traverse((object) => {
    if (
      object instanceof THREE.Mesh ||
      object instanceof THREE.Line ||
      object instanceof THREE.Points
    ) {
      geometries.add(object.geometry);
      for (const material of Array.isArray(object.material)
        ? object.material
        : [object.material]) {
        materials.add(material);
        for (const value of Object.values(material))
          if (value instanceof THREE.Texture) textures.add(value);
      }
    }
    if (object instanceof THREE.InstancedMesh) instances.add(object);
    if (
      object instanceof THREE.DirectionalLight ||
      object instanceof THREE.SpotLight ||
      object instanceof THREE.PointLight
    )
      shadows.add(object.shadow);
    if (object instanceof THREE.Scene) {
      if (object.environment instanceof THREE.Texture)
        textures.add(object.environment);
      if (object.background instanceof THREE.Texture)
        textures.add(object.background);
    }
  });
  return { geometries, materials, textures, instances, shadows };
}

function images(textures: Iterable<THREE.Texture>) {
  const result = new Set<unknown>();
  for (const texture of textures) {
    const data: unknown = texture.source.data;
    for (const image of Array.isArray(data) ? data : [data]) result.add(image);
  }
  return result;
}

/** Detach root first; retained roots protect resources still used elsewhere. */
export function disposeObject(
  root: THREE.Object3D,
  retained: THREE.Object3D[] = [],
) {
  const owned = resources(root);
  const shared = retained.map(resources);
  const protectedImages = new Set(
    shared.flatMap((r) => [...images(r.textures)]),
  );
  const releasedTextures = new Set<THREE.Texture>();
  for (const kind of [
    'instances',
    'shadows',
    'geometries',
    'materials',
    'textures',
  ] as const) {
    const protectedResources = new Set<unknown>(
      shared.flatMap((r) => [...r[kind]]),
    );
    for (const resource of owned[kind]) {
      if (protectedResources.has(resource)) continue;
      resource.dispose();
      if (kind === 'textures') releasedTextures.add(resource as THREE.Texture);
    }
  }
  // Texture.dispose() only releases its GPU allocation, not the decoded bitmap.
  for (const image of images(releasedTextures)) {
    if (
      !protectedImages.has(image) &&
      image &&
      typeof image === 'object' &&
      'close' in image &&
      typeof image.close === 'function'
    )
      image.close();
  }
}
