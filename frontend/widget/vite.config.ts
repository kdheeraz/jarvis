import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: path.resolve(__dirname, 'src/index.tsx'),
      name: 'JarvisWidget',
      formats: ['iife'],
      fileName: () => 'widget.js',
    },
    outDir: path.resolve(__dirname, '../public/widget'),
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});
