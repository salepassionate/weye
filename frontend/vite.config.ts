import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Forward development API requests to FastAPI.
  server: { proxy: { '/api': { target: 'http://localhost:8000', rewrite: path => path.replace(/^\/api/, '') } } }
});
