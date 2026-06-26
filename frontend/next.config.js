/** @type {import('next').NextConfig} */
// Static export. The base path is injected by the Pages deploy workflow from the
// repository's actual Pages configuration (empty for custom-domain/user sites,
// "/<repo>" for project sites), so we make no assumption about hosting. Local
// dev and the live full-stack run at the root.
const basePath = process.env.PAGES_BASE_PATH || "";

const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  ...(basePath ? { basePath, assetPrefix: basePath } : {}),
};

module.exports = nextConfig;
