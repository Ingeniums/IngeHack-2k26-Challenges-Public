// i have only one condition
// i don't wanna see any ad popups
const express = require('express');
const { chromium } = require('playwright');

const app = express();

const port = Number(process.env.BOT_PORT) || 3000;
const timeoutMs = Number(process.env.BOT_TIMEOUT_MS) || 15000;
const waitUntil = process.env.BOT_NAVIGATION_WAIT_UNTIL || 'domcontentloaded';
const botAppOrigin = (process.env.BOT_APP_ORIGIN || 'http://localhost:8090').replace(/\/$/, '');
const botSecret = process.env.BOT_SECRET || 'redacted-bot-secret';

function normalizeUrl(raw) {
  if (typeof raw !== 'string') {
    return null;
  }
  const value = raw.trim();
  if (!value) {
    return null;
  }
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    return null;
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return null;
  }
  return parsed.toString();
}

async function installPopupBlockers(context) {
  await context.addInitScript(() => {
    const blockedOpen = () => null;
    Object.defineProperty(window, 'open', {
      configurable: false,
      enumerable: true,
      writable: false,
      value: blockedOpen,
    });
  });
}

async function visitUrl(url) {
  const disabledFeatures = [
    'HttpsUpgrades',
    'HttpsFirstBalancedModeAutoEnable',
    'HttpsFirstModeIncognito',
    'HttpsFirstModeV2ForEngagedSites',
    'BlockThirdPartyCookies',
    'ImprovedCookieControls',
    'ThirdPartyStoragePartitioning',
    'TrackingProtection3pcd',
    'SameSiteByDefaultCookies',
    'CookiesWithoutSameSiteMustBeSecure',
    'SchemefulSameSite',
  ].join(',');

  const browser = await chromium.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-dev-shm-usage',
      `--disable-features=${disabledFeatures}`,
    ],
  });

  try {
    const context = await browser.newContext();
    await installPopupBlockers(context);
    const flagUrl = new URL('flag.php', `${botAppOrigin}/`);
    const authResponse = await context.request.post(flagUrl.toString(), {
      form: { secret: botSecret },
      timeout: timeoutMs,
    });

    if (!authResponse.ok()) {
      throw new Error(`failed to set bot cookie via ${flagUrl.toString()}`);
    }

    const page = await context.newPage();
    context.on('page', (popup) => {
      if (popup === page) {
        return;
      }
      console.log(`blocked popup while visiting ${url}`);
      void popup.close().catch(() => {});
    });
    const response = await page.goto(url, { waitUntil, timeout: timeoutMs });
    await page.waitForTimeout(1200);
    await context.close();

    return {
      ok: true,
      url,
      status: response ? response.status() : null,
    };
  } finally {
    await browser.close();
  }
}

app.use(express.json({ limit: '256kb' }));
app.use(express.urlencoded({ extended: false, limit: '256kb' }));

app.get('/', (req, res) => {
  res.json({
    ok: true,
    endpoints: ['GET /health', 'POST /visit'],
  });
});

app.get('/health', (req, res) => {
  res.json({ ok: true });
});

app.post('/visit', async (req, res) => {
  const url = normalizeUrl(req.body && req.body.url);
  if (!url) {
    res.status(400).json({ ok: false, error: 'url must be a valid http/https URL' });
    return;
  }

  try {
    const result = await visitUrl(url);
    console.log(`visited ${url} status=${result.status}`);
    res.json(result);
  } catch (err) {
    const message = err && err.message ? err.message : 'visit failed';
    console.error(`failed ${url}: ${message}`);
    res.status(500).json({ ok: false, error: message });
  }
});

app.listen(port, () => {
  console.log(`Playwright bot listening on ${port}`);
});
