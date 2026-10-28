import {
  Vector2,
  WebGLRenderTarget,
  HalfFloatType,
  type WebGLRenderer,
  type Scene,
  type PerspectiveCamera,
} from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { SAOPass } from 'three/addons/postprocessing/SAOPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

/** Loaded only for the explicit fine tier. No targets or passes in auto/smooth. */
export function createPostprocessing(
  renderer: WebGLRenderer,
  scene: Scene,
  camera: PerspectiveCamera,
) {
  const target = new WebGLRenderTarget(1, 1, {
    type: HalfFloatType,
    samples: 4,
  });
  const composer = new EffectComposer(renderer, target);
  const beauty = new RenderPass(scene, camera);
  const ao = new SAOPass(scene, camera);
  Object.assign(ao.params, {
    saoIntensity: 0.018,
    saoBias: 0.6,
    saoScale: camera.far / 3,
    saoKernelRadius: 18,
    saoMinResolution: 0.000003,
    saoBlurRadius: 4,
    saoBlurStdDev: 2,
    saoBlurDepthCutoff: 0.00008,
  });
  const bloom = new UnrealBloomPass(new Vector2(1, 1), 0.14, 0.25, 1.35);
  // Isolated non-finite HDR pixels must not spread across every bloom mip.
  // Keep valid samples unchanged, including values above the display range.
  bloom.materialHighPassFilter.fragmentShader =
    bloom.materialHighPassFilter.fragmentShader.replace(
      'vec4 texel = texture2D( tDiffuse, vUv );',
      `vec4 texel = texture2D( tDiffuse, vUv );
      if (any(isnan(texel)) || any(isinf(texel))) {
        gl_FragColor = vec4(defaultColor, defaultOpacity);
        return;
      }`,
    );
  bloom.enabled = false;
  const output = new OutputPass();
  composer.addPass(beauty);
  composer.addPass(ao);
  composer.addPass(bloom);
  composer.addPass(output);
  function resize() {
    const size = renderer.getSize(new Vector2());
    const ratio = renderer.getPixelRatio();
    composer.setPixelRatio(ratio);
    composer.setSize(size.x, size.y);
    bloom.setSize(
      Math.max(1, Math.floor((size.x * ratio) / 2)),
      Math.max(1, Math.floor((size.y * ratio) / 2)),
    );
    // Composer sizes every pass; override only AO, keeping beauty/output sharp.
    ao.setSize(
      Math.max(1, Math.floor((size.x * ratio) / 2)),
      Math.max(1, Math.floor((size.y * ratio) / 2)),
    );
  }
  resize();
  return {
    resize,
    setNight(on: boolean) {
      bloom.enabled = on;
    },
    render() {
      // Near plane and view offsets change with camera composition.
      ao.saoMaterial.uniforms.cameraInverseProjectionMatrix.value.copy(
        camera.projectionMatrixInverse,
      );
      const shadowUpdate = renderer.shadowMap.autoUpdate;
      beauty.render(
        renderer,
        composer.writeBuffer,
        composer.readBuffer,
        0,
        false,
      );
      // RenderPass above updates shadows once; the normal pass must not repeat it.
      renderer.setRenderTarget(null);
      renderer.shadowMap.autoUpdate = false;
      beauty.enabled = false;
      try {
        composer.render();
      } finally {
        beauty.enabled = true;
        renderer.shadowMap.autoUpdate = shadowUpdate;
      }
    },
    dispose() {
      beauty.dispose();
      ao.dispose();
      bloom.dispose();
      output.dispose();
      composer.dispose();
    },
  };
}
