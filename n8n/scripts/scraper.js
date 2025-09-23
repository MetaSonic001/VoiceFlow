const puppeteer = require('puppeteer');
const { execSync } = require('child_process');
const fs = require('fs');

(async () => {
  const url = process.argv[2];
  try {
    const browser = await puppeteer.launch({
      headless: true,
      executablePath: process.env.PUPPETEER_EXECUTABLE_PATH,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0');
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 });
    const html = await page.content();
    await browser.close();

    // Use Trafilatura via shell for text extraction
    const tempFile = '/tmp/page.html';
    fs.writeFileSync(tempFile, html);
    const text = execSync(`trafilatura -i ${tempFile}`, { encoding: 'utf8' }).trim();
    fs.unlinkSync(tempFile);

    if (!text) throw new Error('No content extracted');
    console.log(JSON.stringify({ text, url }));
  } catch (e) {
    console.log(JSON.stringify({ error: e.message, url }));
  }
})();