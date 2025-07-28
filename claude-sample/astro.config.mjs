
import { defineConfig } from 'astro/config';

export default defineConfig({
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
        '.replit.dev'
      ],
      fs: {
        allow: [
          // Allow serving files from the workspace root
          '/home/runner/workspace',
          // Allow serving Astro runtime files
          '/home/runner/workspace/node_modules'
        ]
      }
    }
  }
});
