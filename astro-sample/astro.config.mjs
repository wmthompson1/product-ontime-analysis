import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  integrations: [react(), tailwind()],
  server: {
    port: 3000,
    host: true
  },
  vite: {
    define: {
      __FLASK_API_URL__: JSON.stringify(
        process.env.NODE_ENV === 'production' 
          ? 'https://your-production-api.com' 
          : 'http://localhost:5000'
      )
    }
  }
});