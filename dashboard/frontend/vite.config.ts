import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/ws': { target: 'ws://127.0.0.1:8000', ws: true } } },
  build: { chunkSizeWarningLimit: 560, rollupOptions: { output: { manualChunks(id) {
    if (id.includes('/node_modules/echarts/')) return 'charts';
    if (id.includes('/node_modules/react/') || id.includes('/node_modules/react-dom/')) return 'react';
    if (id.includes('/node_modules/lucide-react/')) return 'icons';
  } } } },
});
