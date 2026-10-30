# Deploy

The site is deployed to GitHub Pages by `.github/workflows/pages.yml` on every push to
`main` (or manually via "Run workflow"). One-time setup: repository Settings → Pages →
Build and deployment → Source: **GitHub Actions**.

The workflow verifies the input checksums, reruns the full pipeline and publishes
`dist/index.html` plus `licenses/`. The page is a single self-contained HTML file
(data and ECharts embedded), so any static host works: upload `dist/index.html`
(and the licenses) after running the build commands in the README. Party logos
load remotely from polimeter.co.il; names and ballot letters show without them.
