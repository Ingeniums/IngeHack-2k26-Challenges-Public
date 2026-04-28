const puppeteer = require("puppeteer");

const OAUTH_URL = process.env.OAUTH_URL || "http://oauth-provider:3001";
const VICTIM_URL = process.env.VICTIM_URL || "http://victim:3000";
const BOT_SECRET = process.env.BOT_SECRET || "bot_secret_cookie_val";
const INTERACTION_WINDOW_MS = 5000;
const POLL_INTERVAL_MS = 200;
const APPROVE_REACTION_DELAY_MS = 1500;

async function visit(url) {
    let browser;
    let context;
    try {
        browser = await puppeteer.launch({
            headless: "new",
            defaultViewport: null,
            args: [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--use-angle=swiftshader",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-first-run",
                "--window-size=1920,1080",
                "--start-maximized",
                "--disable-popup-blocking"
            ]
        });

        const setupInterception = async (page) => {

        };

        context = await browser.createIncognitoBrowserContext();
        const page = await context.newPage();
        await setupInterception(page);

        browser.on('targetcreated', async (target) => {
            if (target.type() === 'page' && target.browserContext() === context) {
                const newPage = await target.page();
                if (newPage) await setupInterception(newPage);
            }
        });

        page.on('console', msg =>

            await page.goto(`${VICTIM_URL}/`);
        await page.setCookie({
            name: "admin_secret",
            value: BOT_SECRET,
            domain: "rumpelstiltskin-app.ctf.ingeniums.club",
            httpOnly: true
        });


        await page.goto(`${OAUTH_URL}/login`);
        await page.type('input[name="username"]', "admin");
        await page.type('input[name="password"]', "adminpass123");
        await Promise.all([
            page.click('button[type="submit"]'),
            page.waitForNavigation({ waitUntil: "networkidle0" })
        ]);

        await page.goto(url, { waitUntil: "networkidle0", timeout: 10000 });

        await driveInteractionWindow(context);

        await new Promise(r => setTimeout(r, 1000));
    } catch (err) {
        console.error("[Bot] Error during visit:", err);
    } finally {
        if (browser) await browser.close();
    }
}

async function driveInteractionWindow(context) {
    const deadline = Date.now() + INTERACTION_WINDOW_MS;
    const pageState = new WeakMap();

    while (Date.now() < deadline) {
        const activePages = await context.pages();
        let progress = false;

        for (const page of activePages) {
            progress = (await interactWithPage(page, pageState)) || progress;
        }

        if (!progress) {
            await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
        }
    }
}

async function interactWithPage(page, pageState) {
    if (page.isClosed()) return false;

    const state = pageState.get(page) || {
        loginClicked: false,
        approveClicked: false,
        approveSeenAt: null
    };
    pageState.set(page, state);

    let progress = false;

    if (!state.loginClicked) {
        const loginClicked = await clickWhenReady(page, '#loginBtn');
        if (loginClicked) {
            state.loginClicked = true;
            progress = true;
        }
    }

    if (!state.approveClicked) {
        const approveStatus = await clickApproveButton(page, state);
        if (approveStatus === "waiting") {
            progress = true;
        }

        if (approveStatus === "clicked") {
            state.approveClicked = true;
            progress = true;
        }
    }

    return progress;
}

async function clickWhenReady(page, selector) {
    const handle = await page.$(selector);
    if (!handle) return false;

    try {
        const isClickable = await page.evaluate((element) => {
            if (!element || !element.isConnected) return false;
            if (element.disabled) return false;

            const style = window.getComputedStyle(element);
            if (style.visibility === "hidden" || style.display === "none") return false;

            const rect = element.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return false;
            return true;
        }, handle);

        if (!isClickable) return false;

        await handle.click();
        return true;
    } catch (_error) {
        return false;
    } finally {
        await handle.dispose().catch(() => {});
    }
}

async function clickApproveButton(page, state) {
    const handles = await page.$$("button");
    try {
        for (const handle of handles) {
            const isApproveButton = await page.evaluate((element) => {
                if (!element || !element.isConnected || element.disabled) return false;

                const style = window.getComputedStyle(element);
                if (style.visibility === "hidden" || style.display === "none") return false;

                const rect = element.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return false;

                return /approve/i.test((element.textContent || "").trim());
            }, handle);

            if (!isApproveButton) continue;

            if (state.approveSeenAt === null) {
                state.approveSeenAt = Date.now();
                return "waiting";
            }

            if (Date.now() - state.approveSeenAt < APPROVE_REACTION_DELAY_MS) {
                return "waiting";
            }

            await handle.click();
            return "clicked";
        }
    } catch (_error) {
        return "idle";
    } finally {
        await Promise.all(handles.map(handle => handle.dispose().catch(() => {})));
    }

    state.approveSeenAt = null;
    return "idle";
}

module.exports = { visit };
