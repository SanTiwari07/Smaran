/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_USE_MOCK?: string;
  readonly VITE_GATEWAY_URL?: string;
  readonly VITE_DEVICE_A_URL?: string;
  readonly VITE_DEVICE_B_URL?: string;
}
