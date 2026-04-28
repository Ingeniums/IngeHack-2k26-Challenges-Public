const crypto = require("crypto");
const express = require("express");
const cookieParser = require("cookie-parser");

const app = express();
app.use(cookieParser());
app.use(express.urlencoded({ extended: false }));
app.use(express.json());
app.use(frameOptionsExcept404);

const PORT = process.env.PORT || 3001;

// In-memory "authorization code" store.
// code -> { user, createdAt }
const codes = new Map();
const sessions = new Map();
const attackerUsers = new Map();

const ADMIN_USER = {
  username: "admin",
  password: "f8788078197142f5473b77ff6948ff6bd9ae1e1215cd8c9daccc3d2ff02cf94b",
  role: "admin"
};

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

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[char]));
}

function getUser(username) {
  if (username === ADMIN_USER.username) return ADMIN_USER;

  const user = attackerUsers.get(username);
  return user ? { username, ...user } : null;
}

function validateUsername(username) {
  return /^[a-zA-Z0-9_][a-zA-Z0-9_.-]{2,31}$/.test(username);
}

function validatePassword(password) {
  return typeof password === "string" && password.length >= 8 && password.length <= 128;
}

function issueCode(user) {
  const code = crypto.randomBytes(16).toString("hex");
  codes.set(code, { user, createdAt: Date.now() });
  return code;
}

function renderAuthPage({ returnTo = "/", error = "", notice = "" } = {}) {
  const safeReturnTo = escapeHtml(returnTo);
  const safeError = escapeHtml(error);
  const safeNotice = escapeHtml(notice);

  return `
    <!doctype html>
    <title>Login - SSO</title>
    <style>
      :root{
        --bg:#050805; --text:#4ade80; --muted:#166534; --border:#1a331a;
        --scanline: rgba(74, 222, 128, 0.05); --warn:#f97316; --good:#22c55e;
      }
      *{ box-sizing:border-box; border-radius: 0 !important; }
      body{
        margin:0; min-height:100vh; display:grid; place-items:center;
        font-family: 'Courier New', Courier, monospace; color:var(--text);
        background: var(--bg);
        position: relative;
        overflow: hidden;
        padding: 24px;
      }
      body::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: repeating-linear-gradient(0deg, transparent, transparent 1px, var(--scanline) 2px, var(--scanline) 3px);
        pointer-events: none; z-index: 100;
      }
      .shell{
        width:min(860px, 100%); border:2px solid var(--border);
        background: rgba(15, 26, 15, 0.9); padding:24px;
        box-shadow: 5px 5px 0px var(--border);
      }
      .grid{
        display:grid; gap:24px;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      }
      h1, h2 { text-transform: uppercase; margin: 0 0 10px 0; }
      h1 { font-size: 18px; }
      h2 { font-size: 16px; }
      p { color: var(--muted); line-height: 1.5; margin: 0 0 16px 0; }
      input {
        width: 100%; padding: 10px; margin-bottom: 15px;
        background: transparent; border: 2px solid var(--border);
        color: var(--text); font-family: inherit;
      }
      input:focus { border-color: var(--text); outline: none; }
      button {
        width: 100%; padding: 12px; cursor: pointer;
        border: 2px solid var(--text); background: transparent;
        color: var(--text); text-transform: uppercase; font-weight: bold; font-family: inherit;
      }
      button:hover { background: var(--text); color: var(--bg); }
      label { display: block; margin-bottom: 5px; font-size: 12px; text-transform: uppercase; color: var(--muted); }
      .msg{
        margin-bottom: 18px; padding: 12px; border: 2px solid var(--border);
        background: rgba(10, 18, 10, 0.7);
      }
      .msg.error { border-color: var(--warn); color: var(--warn); }
      .msg.notice { border-color: var(--good); color: var(--good); }
      .divider{
        border-top: 2px solid var(--border);
        margin: 18px 0;
      }
      .hint { font-size: 12px; margin-top: 8px; }
    </style>
    <div class="shell">
      <h1>SSO Terminal</h1>
      <p>Admin remains a single reserved identity. New registrations are provisioned as attacker accounts.</p>
      ${safeError ? `<div class="msg error">${safeError}</div>` : ""}
      ${safeNotice ? `<div class="msg notice">${safeNotice}</div>` : ""}
      <div class="grid">
        <section>
          <h2>Sign In</h2>
          <form method="POST" action="/login">
            <input type="hidden" name="return_to" value="${safeReturnTo}">
            <label>System Identity</label>
            <input name="username" required autocomplete="username">

            <label>Access Key</label>
            <input type="password" name="password" required autocomplete="current-password">
            <button type="submit">Initialize Session</button>
          </form>
        </section>
        <section>
          <h2>Register Attacker</h2>
          <form method="POST" action="/register">
            <input type="hidden" name="return_to" value="${safeReturnTo}">
            <label>Attacker Alias</label>
            <input name="username" required autocomplete="username">

            <label>Access Key</label>
            <input type="password" name="password" required autocomplete="new-password">
            <button type="submit">Create Attacker Account</button>
          </form>
          <div class="divider"></div>
          <p class="hint">Use 3-32 letters, numbers, <code>_</code>, <code>-</code>, or <code>.</code>. Passwords must be at least 8 characters.</p>
        </section>
      </div>
    </div>
  `;
}

app.get("/", (_req, res) => {
  res.type("text").send("Secure SSO Provider (challenge)");
});

app.get("/login", (req, res) => {
  const returnTo = req.query.return_to || "/";
  res.status(200).type("html").send(renderAuthPage({ returnTo }));
});

app.post("/login", (req, res) => {
  const username = typeof req.body.username === "string" ? req.body.username.trim() : "";
  const password = typeof req.body.password === "string" ? req.body.password : "";
  const returnTo = typeof req.body.return_to === "string" ? req.body.return_to : "/";
  if (!username || !password) {
    return res.status(400).type("html").send(renderAuthPage({
      returnTo,
      error: "Missing username or password."
    }));
  }

  const user = getUser(username);
  if (!user || user.password !== password) {
    return res.status(401).type("html").send(renderAuthPage({
      returnTo,
      error: "Invalid credentials."
    }));
  }

  // Create a persistent session instead of trusting a user-provided username cookie
  const sessionId = crypto.randomBytes(16).toString("hex");
  sessions.set(sessionId, { username: user.username, role: user.role });

  res.cookie("sso_session", sessionId, { path: "/", SameSite: "Lax", maxAge: 86400000 });
  res.redirect(returnTo || "/");
});

app.post("/register", (req, res) => {
  const username = typeof req.body.username === "string" ? req.body.username.trim() : "";
  const password = typeof req.body.password === "string" ? req.body.password : "";
  const returnTo = typeof req.body.return_to === "string" ? req.body.return_to : "/";

  if (!validateUsername(username)) {
    return res.status(400).type("html").send(renderAuthPage({
      returnTo,
      error: "Choose a username with 3-32 valid characters."
    }));
  }

  if (!validatePassword(password)) {
    return res.status(400).type("html").send(renderAuthPage({
      returnTo,
      error: "Choose a password between 8 and 128 characters."
    }));
  }

  if (username === ADMIN_USER.username) {
    return res.status(409).type("html").send(renderAuthPage({
      returnTo,
      error: "The admin identity is reserved."
    }));
  }

  if (attackerUsers.has(username)) {
    return res.status(409).type("html").send(renderAuthPage({
      returnTo,
      error: "That attacker alias already exists."
    }));
  }

  attackerUsers.set(username, { password, role: "attacker" });

  const sessionId = crypto.randomBytes(16).toString("hex");
  sessions.set(sessionId, { username, role: "attacker" });

  res.cookie("sso_session", sessionId, { path: "/", SameSite: "Lax", maxAge: 86400000 });
  res.redirect(returnTo || "/");
});

// OAuth authorize endpoint
// Expects: redirect_uri, state (optional), client_id (ignored), response_type=code
app.get("/authorize", (req, res) => {
  const redirectUri = req.query.redirect_uri;
  if (typeof redirectUri !== "string" || !redirectUri.startsWith("http")) {
    return res.status(400).type("text").send("Missing/invalid redirect_uri");
  }

  const sessionToken = req.cookies.sso_session;
  const user = sessionToken ? sessions.get(sessionToken) : null;
  if (!user) {
    const loginUrl = new URL("/login", `http://${req.headers.host}`);
    loginUrl.searchParams.set("return_to", req.originalUrl);
    return res.redirect(loginUrl.toString());
  }

  const code = issueCode(user);
  const state = typeof req.query.state === "string" ? req.query.state : "";

  const url = new URL(redirectUri);
  url.searchParams.set("code", code);
  if (state) url.searchParams.set("state", state);

  res.type("html").send(`
    <!doctype html>
    <title>Authorize Access</title>
    <style>
      :root{
        --bg:#050805; --text:#4ade80; --muted:#166534; --border:#1a331a;
        --scanline: rgba(74, 222, 128, 0.05);
      }
      *{ box-sizing:border-box; border-radius: 0 !important; }
      body{
        margin:0; min-height:100vh; display:grid; place-items:center;
        font-family: 'Courier New', Courier, monospace; color:var(--text);
        background: var(--bg);
        position: relative;
        overflow: hidden;
      }
      body::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: repeating-linear-gradient(0deg, transparent, transparent 1px, var(--scanline) 2px, var(--scanline) 3px);
        pointer-events: none; z-index: 100;
      }
      .card{
        width:min(400px, 92vw); border:2px solid var(--border);
        background: rgba(15, 26, 15, 0.9); padding:24px;
        box-shadow: 5px 5px 0px var(--border);
      }
      h2 { font-size: 18px; text-transform: uppercase; margin-top: 0; }
      p { line-height: 1.5; color: var(--muted); }
      b { color: var(--text); }
      button {
        width: 100%; padding: 12px; cursor: pointer; margin-top: 10px;
        border: 2px solid var(--text); background: transparent;
        color: var(--text); text-transform: uppercase; font-weight: bold; font-family: inherit;
      }
      button:hover { background: var(--text); color: var(--bg); }
    </style>
    <div class="card">
      <h2>Authorization Required</h2>
      <p>System identity <b>${escapeHtml(user.username)}</b> is requesting access delegation.</p>
      <p>Confirm uplink to continue.</p>
      <button onclick="window.location.href='${url.toString()}'">Approve Uplink</button>
    </div>
  `);
});

// OAuth token endpoint
// Expects JSON: { code }
app.post("/token", (req, res) => {
  const { code } = req.body || {};
  if (typeof code !== "string") return res.status(400).json({ error: "bad_code" });

  console.log("==== codes ===")
  console.log(codes)
  const record = codes.get(code);
  console.log("==== record ===")
  console.log(record)
  if (!record) return res.status(400).json({ error: "invalid_code" });

  // one-time use
  codes.delete(code);
  res.json({
    user: {
      username: record.user.username,
      role: record.user.role
    }
  });
});

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`oauth-provider listening on :${PORT}`);
});
