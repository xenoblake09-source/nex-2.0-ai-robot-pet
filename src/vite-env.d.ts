/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_NEX_API_BASE?: string;
  readonly VITE_NEX_WAKE_WORD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
