import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      '0.0.0.0',
      '.replit.dev',
      '.riker.replit.dev',
      '9885a95f-5ab2-441a-b79a-7fe6a57d2320-00-133f632yjz64j.riker.replit.dev'
    ],
    host: '0.0.0.0',
    port: 4321,
    cors: true
  }
});