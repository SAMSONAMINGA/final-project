/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable experimental app dir warnings
  experimental: {
    appDir: true,
  },
  
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  
  // Optimization for Vercel
  swcMinify: true,
  
  // Image optimization
  images: {
    domains: [
      'localhost',
      'floodguard-backend.onrender.com',
      'res.cloudinary.com',
    ],
  },
  
  // Headers for security
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
