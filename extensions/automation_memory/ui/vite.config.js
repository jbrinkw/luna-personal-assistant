import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command, mode }) => {
  // Get port from CLI args or use default
  const port = process.env.PORT ? parseInt(process.env.PORT) : 5200;
  
  return {
    plugins: [react()],
    server: {
      port: port,
      host: '127.0.0.1',
      strictPort: true,
    },
  };
});

