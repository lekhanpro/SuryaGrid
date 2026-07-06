/** @type {import('next').NextConfig} */
// Two build modes:
//   - Default (Docker / local full-stack): a normal Next.js server build so the app
//     can be served with `next start` and talk to the live backend.
//   - STATIC_EXPORT=true (GitHub Pages): static HTML export to `out/`. The base path
//     is injected by the Pages deploy workflow from the repo's Pages configuration.
const staticExport = process.env.STATIC_EXPORT === "true";
const basePath = process.env.PAGES_BASE_PATH || "";

const nextConfig = {
  ...(staticExport ? { output: "export" } : {}),
  images: { unoptimized: true },
  ...(staticExport && basePath ? { basePath, assetPrefix: basePath } : {}),
};

module.exports = nextConfig;
