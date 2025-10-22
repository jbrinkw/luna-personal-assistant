import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // Load .env file from parent directory (repo root)
  const env = loadEnv(mode, '../', '');
  
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
    server: {
      port: 5173,
      host: '127.0.0.1',  // Localhost only - access via Caddy proxy
      strictPort: true,  // Fail if port is in use instead of trying next port
      ...(allowedHosts.length > 0 && { allowedHosts }),  // Only add if we have tunnel hosts
    },
  };
});

