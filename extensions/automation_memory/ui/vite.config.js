import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command, mode }) => {
  // Get port from CLI args or use default
  const port = process.env.PORT ? parseInt(process.env.PORT) : 5200;
  
  return {
    plugins: [react()],
    server: {
      port: port,
      host: '0.0.0.0',  // Allow network access
      strictPort: true,
    },
  };
});

