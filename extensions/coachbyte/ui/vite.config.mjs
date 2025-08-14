import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiPort = process.env.COACH_API_PORT || process.env.VITE_COACH_API_PORT || '3001';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': `http://localhost:${apiPort}`
    }
  }
});





