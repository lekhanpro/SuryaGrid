/** @type {import('next').NextConfig} */
// Served at the root path `/` in all environments.
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
};

module.exports = nextConfig;
