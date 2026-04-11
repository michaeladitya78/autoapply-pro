import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  images: {
    // Bug 6 fix: replaced deprecated images.domains with remotePatterns
    remotePatterns: [
      {
        protocol: "https",
        hostname: "img.clerk.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "images.clerk.dev",
        pathname: "/**",
      },
    ],
  },
  // Clerk env var references — these must be set in your deployment environment
  // NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY — set in .env.local / Vercel env vars
  // CLERK_SECRET_KEY                  — set in .env.local / Vercel env vars
  // NEXT_PUBLIC_CLERK_SIGN_IN_URL     — /sign-in
  // NEXT_PUBLIC_CLERK_SIGN_UP_URL     — /sign-up
  // NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL — /dashboard
  // NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL — /onboarding  (or /dashboard)
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
