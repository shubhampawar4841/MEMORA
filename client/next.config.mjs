import path from "node:path"
import { fileURLToPath } from "node:url"

const clientRoot = path.dirname(fileURLToPath(import.meta.url))

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  turbopack: {
    root: clientRoot,
  },
}

export default nextConfig
