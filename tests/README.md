# Optional browser smoke test

These tests are optional; the Python analysis/build/package scripts need no npm dependencies.
Use Node.js 20+ (the historical browser run used Node 25 and Playwright 1.62.1).

```sh
npm install
npx playwright install chromium
npm test
```

For an already installed Chrome/Chromium, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`
to its executable instead of installing the bundled browser. This is optional;
the test has no machine-specific executable path.

The test blocks external image requests intentionally, verifies local ECharts loading,
checks Hebrew/English modes, cluster and bloc selection, the nationwide reference, the
year switch, the Sankey at both levels, the scatter, and locality search on a phone viewport.
If only `playwright-core` is installed it is used instead of `playwright`.
