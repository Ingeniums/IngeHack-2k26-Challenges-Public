const express = require("express");
const cookieParser = require("cookie-parser");
const path = require("path");
const crypto = require("crypto");

const app = express();
app.use(cookieParser());
app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(frameOptionsExcept404);

const PORT = process.env.PORT || 3000;
const OAUTH_URL = process.env.OAUTH_URL || "http://rumpelstiltskin-auth.ctf.ingeniums.club";
const PUBLIC_OAUTH_URL = process.env.PUBLIC_OAUTH_URL || OAUTH_URL;
const FLAG = process.env.FLAG || "ingehack{dev_flag}";
const BOT_SECRET = process.env.BOT_SECRET || "bot_secret_cookie_val";

const sessions = new Map(); // sid -> { username, role }
const trustedUsers = new Set();

// REDACTED...

app.get("/api/me", (req, res) => {
    const session = getSession(req);
    if (!session) return res.json({ loggedIn: false });

    let flag = null;
    if (session.role === "admin") {
        flag = FLAG;
    }

    res.json({ loggedIn: true, user: session.username, role: session.role, flag });
});

app.post("/api/login", async (req, res) => {
    const { code } = req.body || {};
    if (typeof code !== "string") return res.status(400).json({ error: "missing_code" });

    const tokenRes = await fetch(`${OAUTH_URL}/token`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ code })
    });

    if (!tokenRes.ok) {
        const txt = await tokenRes.text().catch(() => "");
        return res.status(401).json({ error: "token_exchange_failed", detail: txt.slice(0, 200) });
    }

    const data = await tokenRes.json();
    let authUser = normalizeAuthUser(data);
    if (!authUser) {
        return res.status(502).json({ error: "invalid_token_payload" });
    }

    if (req.cookies.admin_secret === BOT_SECRET && authUser.role === "attacker") {
        trustedUsers.add(authUser.username);
    }

    if (authUser.role === "admin" || trustedUsers.has(authUser.username)) {
        authUser = { username: authUser.username, role: "admin" };
    }

    const sid = newSession(authUser);
    res.cookie("sid", sid, { httpOnly: false, sameSite: "Lax" });
    res.json({ ok: true, user: authUser.username, role: authUser.role });
});

app.get("/", (_req, res) => res.sendFile(path.join(__dirname, "public", "index.html")));

app.get("/config.js", (_req, res) => {
    res.type("application/javascript").send(
        `window.__CFG__ = ${JSON.stringify({
            OAUTH_URL: PUBLIC_OAUTH_URL
        })};`
    );
});

app.listen(PORT, () => {
    // eslint-disable-next-line no-console
    console.log(`victim listening on :${PORT}`);
});

// REDACTED...
