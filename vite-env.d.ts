/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Content hash of public/data, set by build-pages.mjs for cache busting. */
  readonly VITE_DATA_VERSION?: string;
}
