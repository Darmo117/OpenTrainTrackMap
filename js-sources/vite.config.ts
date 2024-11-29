import { defineConfig } from "vite";

export default defineConfig({
  publicDir: "../ottm/static/ottm",
  base: "../ottm/static/ottm",
  build: {
    outDir: "../ottm/static/ottm",
    rollupOptions: {
      input: "src/index.ts", // Entry point
      output: {
        entryFileNames: "bundle-[name].js", // [name] = name of input file
        assetFileNames: "bundle-[name].[ext]",
        manualChunks: {
          "maplibre-gl": ["maplibre-gl"],
          jquery: ["jquery"],
        },
        chunkFileNames: "bundle-dep-[name].js",
      },
    },
  },
});
