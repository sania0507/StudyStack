import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import path from "node:path"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // Lets us write `import Button from "@/components/Button"` instead of "../../components/Button"
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  // The preview looks for the dev server on port 3000, so pin it there.
  server: { host: true, port: 3000, strictPort: true, allowedHosts: true },
})
