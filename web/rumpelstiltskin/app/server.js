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

function frameOptionsExcept404(_req, res, next) {
    const originalWriteHead = res.writeHead.bind(res);
    const originalEnd = res.end.bind(res);

    function applyFrameOptions(statusCode) {
        if (statusCode === 404) {
            res.removeHeader("X-Frame-Options");
            return;
        }

        if (!res.hasHeader("X-Frame-Options")) {
            res.setHeader("X-Frame-Options", "Deny");
        }
    }

    res.writeHead = function writeHead(statusCode, ...args) {
        applyFrameOptions(typeof statusCode === "number" ? statusCode : res.statusCode);
        return originalWriteHead(statusCode, ...args);
    };

    res.end = function end(...args) {
        if (!res.headersSent) {
            applyFrameOptions(res.statusCode);
        }

        return originalEnd(...args);
    };

    next();
}

function newSession(user) {
    const sid = crypto.randomBytes(16).toString("hex");
    sessions.set(sid, { username: user.username, role: user.role });
    return sid;
}

function getSession(req) {
    const sid = req.cookies.sid;
    if (typeof sid !== "string") return null;
    return sessions.get(sid) || null;
}

/* ── GET /api/me ────────────────────────────────────────────────── */
app.get("/api/me", (req, res) => {
    const session = getSession(req);
    if (!session) return res.json({ loggedIn: false });

    let flag = null;
    if (session.role === "admin") {
        flag = FLAG;
    }

    res.json({ loggedIn: true, user: session.username, role: session.role, flag });
});

/* ── POST /api/login  (OAuth code → session) ────────────────────── */
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

app.use(
    express.static(path.join(__dirname, "public"), {
        setHeaders(res, filePath) {
            if (filePath.endsWith(".html")) {
                res.setHeader("cache-control", "no-store");
            }
        }
    })
);

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

function normalizeAuthUser(data) {
    if (data && data.user && typeof data.user === "object") {
        const username = typeof data.user.username === "string" ? data.user.username : "";
        const role = data.user.role;
        if (!username || (role !== "admin" && role !== "attacker")) return null;
        return { username, role };
    }

    if (data && typeof data.user === "string") {
        if (!data.user) return null;
        return {
            username: data.user,
            role: data.user === "admin" ? "admin" : "attacker"
        };
    }

    return null;
}
