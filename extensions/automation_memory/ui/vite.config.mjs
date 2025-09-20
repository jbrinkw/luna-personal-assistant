import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiPort = process.env.AM_API_PORT || process.env.VITE_AM_API_PORT || '3051';

const uiPort = process.env.AM_UI_PORT || '8033';

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





