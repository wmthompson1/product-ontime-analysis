import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  integrations: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0'
  },
  vite: {
    server: {
      host: '0.0.0.0',
      port: 3000,
      allowedHosts: 'all'
    }
  }
});