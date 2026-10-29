// The application always supplies its own GLTF decoder. Resolve Three's default
// URL expressions to that same public directory before Vite emits duplicate files.
export function campusDracoAssets(basePath = '') {
  return {
    name: 'campus-draco-assets',
    enforce: 'pre',
    transform(source, id) {
      if (
        !id
          .replaceAll('\\', '/')
          .endsWith('/three/examples/jsm/loaders/DRACOLoader.js')
      )
        return;
      let count = 0;
      const code = source.replace(
        /new URL\(\s*'\.\.\/libs\/draco\/(?:gltf\/)?(draco_(?:decoder\.(?:wasm|js)|wasm_wrapper\.js))',\s*import\.meta\.url\s*\)\.toString\(\)/g,
        (_, file) => {
          count++;
          return JSON.stringify(`${basePath}/draco/${file}`);
        },
      );
      // Fail visibly on upstream changes instead of silently shipping duplicates.
      if (count !== 5)
        throw new Error(`Unexpected DRACOLoader asset URLs: ${count}`);
      return { code, map: null };
    },
  };
}
