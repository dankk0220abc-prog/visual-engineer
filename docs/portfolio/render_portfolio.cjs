const { createRequire } = require("node:module");
const { join } = require("node:path");

const webRequire = createRequire(
  join(__dirname, "../../apps/web/package.json"),
);
const { chromium } = webRequire("@playwright/test");

const source = join(__dirname, "VisualEngineer_Interview_Portfolio.html");
const output = join(__dirname, "VisualEngineer_Interview_Portfolio.pdf");

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 1600, height: 900 },
      deviceScaleFactor: 1,
    });
    await page.goto(`file://${source}`, { waitUntil: "networkidle" });
    await page.pdf({
      path: output,
      width: "13.333in",
      height: "7.5in",
      printBackground: true,
      preferCSSPageSize: true,
      margin: { top: "0", right: "0", bottom: "0", left: "0" },
    });
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
