/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  
  // Enable static export for SWA
  output: 'export',
  
  // Conditionally apply rewrites only for development
  ...(process.env.NODE_ENV === 'development' ? {
    async rewrites() {
      return [
        {
          source: '/api/:path*',
          destination: 'http://127.0.0.1:5328/api/:path*',
        },
      ];
    }
  } : {}),
  
  // Optimize for Azure Static Web Apps
  env: {
    TENANT_ID: process.env.TENANT_ID,
    DATA_AGENT_URL: process.env.DATA_AGENT_URL,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  }
}

export default nextConfig