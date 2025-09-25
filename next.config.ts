import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'export',
  reactStrictMode: true,
  images: {
    unoptimized: true,
  },
  // Remove rewrites as they don't work with static export
  // API routing will be handled by Azure Static Web Apps configuration
}

export default nextConfig