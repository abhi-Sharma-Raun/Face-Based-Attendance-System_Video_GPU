import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  server: {
    allowedHosts: [
      'alverta-radioscopic-bemusedly.ngrok-free.dev'
    ]
  },
  build: {
    rollupOptions: {
      input: {
        // ADDED: Explicitly map all HTML entry points for the bundler pipeline
        main: resolve(__dirname, 'index.html'),
        student: resolve(__dirname, 'student.html'),
        teacher: resolve(__dirname, 'teacher.html'),
        admin: resolve(__dirname, 'admin.html')
      }
    }
  }
})