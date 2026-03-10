/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
    NEXT_PUBLIC_GRAPHQL_URL: process.env.NEXT_PUBLIC_GRAPHQL_URL || '/graphql',
  },
  async rewrites() {
    // Proxy /graphql and /api to the backend service.
    // In production with nginx, nginx handles this directly.
    // In dev or standalone mode, Next.js proxies to the backend.
    const backendUrl = process.env.BACKEND_URL || 'http://backend:8000'
    return [
      {
        source: '/graphql',
        destination: `${backendUrl}/graphql`,
      },
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig