import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiPort = process.env.AM_API_PORT || process.env.VITE_AM_API_PORT || '3051';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 8033,
    proxy: {
      '/api': `http://localhost:${apiPort}`
    }
  }
});





