import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiPort = process.env.COACH_API_PORT || process.env.VITE_COACH_API_PORT || '3001';

const uiPort = process.env.COACH_UI_PORT || '8031';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: parseInt(uiPort),
    proxy: {
      '/api': `http://localhost:${apiPort}`
    }
  }
});





