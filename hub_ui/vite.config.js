import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',  // Allow network access
    strictPort: true,  // Fail if port is in use instead of trying next port
  },
});

