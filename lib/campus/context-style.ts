import {
  CanvasTexture,
  Color,
  Vector4,
  type MeshStandardMaterial,
} from 'three';
import type { CampusBoundary } from './boundary';

/** A presentation-only mask: the existing campus outline stays geographically unchanged. */
export function createContextStyle() {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1024;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = 'white';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const mask = new CanvasTexture(canvas);
  mask.flipY = false;
  const bounds = new Vector4(0, 0, 1, 1);
  const applied = new WeakSet<MeshStandardMaterial>();
  return {
    setBoundary(data: CampusBoundary) {
      const points = data.rings.flat();
      const xs = points.map((p) => p[0]),
        ys = points.map((p) => p[1]);
      const x0 = Math.min(...xs) - 10,
        y0 = Math.min(...ys) - 10;
      bounds.set(x0, y0, Math.max(...xs) - x0 + 10, Math.max(...ys) - y0 + 10);
      ctx.fillStyle = 'black';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = 'white';
      ctx.beginPath();
      for (const ring of data.rings) {
        ring.forEach(([x, y], i) => {
          const u = ((x - bounds.x) / bounds.z) * canvas.width;
          const v = ((y - bounds.y) / bounds.w) * canvas.height;
          if (i === 0) ctx.moveTo(u, v);
          else ctx.lineTo(u, v);
        });
        ctx.closePath();
      }
      ctx.fill('evenodd');
      mask.needsUpdate = true;
    },
    apply(material: MeshStandardMaterial) {
      if (
        !['grass', 'road', 'asphalt'].includes(material.name) ||
        applied.has(material)
      )
        return;
      applied.add(material);
      material.onBeforeCompile = (shader) => {
        shader.uniforms.contextMask = { value: mask };
        shader.uniforms.contextBounds = { value: bounds };
        shader.uniforms.contextTint = {
          value: new Color(material.name === 'grass' ? '#b9c0ab' : '#a3aaa3'),
        };
        shader.vertexShader =
          'varying vec2 campusPosition;\n' + shader.vertexShader;
        shader.vertexShader = shader.vertexShader.replace(
          '#include <worldpos_vertex>',
          '#include <worldpos_vertex>\ncampusPosition = (modelMatrix * vec4(transformed, 1.0)).xz * vec2(1.0, -1.0);',
        );
        shader.fragmentShader =
          'uniform sampler2D contextMask;\nuniform vec4 contextBounds;\nuniform vec3 contextTint;\nvarying vec2 campusPosition;\n' +
          shader.fragmentShader;
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <map_fragment>',
          `#include <map_fragment>
          vec2 campusUV = (campusPosition - contextBounds.xy) / contextBounds.zw;
          float campusInside = texture2D(contextMask, campusUV).r;
          diffuseColor.rgb = mix(diffuseColor.rgb, contextTint, (1.0 - campusInside) * 0.55);
        `,
        );
      };
      material.customProgramCacheKey = () => 'campus-context-v1';
      material.needsUpdate = true;
    },
    dispose: () => mask.dispose(),
  };
}
