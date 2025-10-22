import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command, mode }) => {
  // Get port from CLI args or use default
  const port = process.env.PORT ? parseInt(process.env.PORT) : 5200;
  
  // Load .env file from repo root (3 levels up: ui -> extension -> extensions -> root)
  const env = loadEnv(mode, '../../../', '');
  
  // Build allowed hosts list - support all deployment modes
  const allowedHosts = [];
  
  // ngrok mode: TUNNEL_HOST
  if (env.TUNNEL_HOST) {
    allowedHosts.push(env.TUNNEL_HOST);
  }
  
  // nip_io or custom_domain mode: PUBLIC_DOMAIN
  if (env.PUBLIC_DOMAIN) {
    allowedHosts.push(env.PUBLIC_DOMAIN);
  }
  
  return {
    plugins: [react()],
    base: '/ext/automation_memory/',
    server: {
      port: port,
      host: '127.0.0.1',  // Bind to localhost only
      strictPort: true,
      ...(allowedHosts.length > 0 && { allowedHosts }),  // Only add if we have tunnel hosts
    },
  };
});

