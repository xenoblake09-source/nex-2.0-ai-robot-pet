import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'ai.nexcompanion.virtualpet',
  appName: 'NEX',
  webDir: 'dist',
  android: {
    allowMixedContent: false,
    backgroundColor: '#000000',
    webContentsDebuggingEnabled: false,
  },
  server: {
    androidScheme: 'https',
  },
};

export default config;
