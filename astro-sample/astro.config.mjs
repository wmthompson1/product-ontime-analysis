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
      allowedHosts: [
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        '9885a95f-5ab2-441a-b79a-7fe6a57d2320-00-133f632yjz64j.riker.replit.dev',
        '.replit.dev'
      ]
    }
  }
});