import { defineConfig } from "vite";

export default defineConfig({
  publicDir: "../ottm/static/ottm/generated/",
  base: "/static/ottm/generated/",
  build: {
    outDir: "../ottm/static/ottm/generated/",
    assetsInlineLimit: 0,
    rollupOptions: {
      input: "src/index.ts", // Entry point
      output: {
        entryFileNames: "[name].js",
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        assetFileNames: ({ name }) => {
          const ext = name?.split(".").at(-1);
          let dir = "";
          switch (ext) {
            case "png":
            case "jpg":
            case "jpeg":
              dir = "images/";
              break;
            case "eot":
            case "ttf":
            case "woff":
            case "woff2":
              dir = "fonts/";
              break;
            case "css":
              dir = "css/";
              break;
          }
          return dir + "[name][extname]";
        },
        manualChunks: {
          "maplibre-gl": ["maplibre-gl"],
          jquery: ["jquery"],
        },
        chunkFileNames: "dep-[name].js",
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        quietDeps: true,
        api: "modern",
      },
    },
  },
});
