const express = require("express");
const { VM } = require("vm2");

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get("/", (req, res) => {
  res.send(`
<!DOCTYPE html>
<html>
<head>
  <title> v1.0 - Sandboxed JS Executor</title>
  <style>
    body { background: #0d0d0d; color: #00ff88; font-family: monospace; padding: 2rem; }
    h1 { color: #00ff88; border-bottom: 1px solid #00ff8844; padding-bottom: 0.5rem; }
    textarea { width: 100%; height: 150px; background: #111; color: #0ff; border: 1px solid #333; padding: 0.5rem; font-family: monospace; }
    button { margin-top: 0.5rem; padding: 0.5rem 1.5rem; background: #003322; color: #00ff88; border: 1px solid #00ff88; cursor: pointer; }
    pre { background: #111; padding: 1rem; border: 1px solid #333; min-height: 60px; white-space: pre-wrap; word-break: break-all; }
    .note { color: #666; font-size: 0.8rem; margin-top: 1rem; }
  </style>
</head>
<body>
  <h1>[ Js v1.0 ]</h1>
  <p>Execute untrusted JavaScript safely inside our powered sandbox.</p>
  <form method="POST" action="/run">
    <textarea name="code" placeholder="Enter your JS code here..."></textarea><br/>
    <button type="submit">&#9654; Execute</button>
  </form>
  <p class="note">Powered by ingeniums@3.10.0 — industry-leading sandbox technology.</p>
</body>
</html>
  `);
});

app.post("/run", async (req, res) => {
  const code = req.body.code || "";

  if (!code.trim()) {
    return res.json({ output: "", error: "No code provided." });
  }

  if (code.length > 4096) {
    return res.json({ output: "", error: "Code too long (max 4096 chars)." });
  }

  let output = "";
  let error = null;

  try {
    const vm = new VM({
      timeout: 5000,
      sandbox: {
        __log: (msg) => { output += String(msg) + "\n"; },
        __done: null,
        __reject: null,
      },
    });

    const wrapped = `
      const console = { log: (...args) => __log(args.join(' ')) };
      (async () => {
        ${code}
      })();
    `;

    const result = vm.run(wrapped);

    if (result && typeof result.then === "function") {
      await Promise.race([
        result,
        new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 5000))
      ]).catch(e => { error = e.message; });
    }

  } catch (e) {
    error = e.message || String(e);
  }

  if (req.headers["content-type"] === "application/json") {
    return res.json({ output, error });
  }

  res.send(`
<!DOCTYPE html>
<html>
<head>
  <title>SafeEval v1.0 - Result</title>
  <style>
    body { background: #0d0d0d; color: #00ff88; font-family: monospace; padding: 2rem; }
    h1 { color: #00ff88; border-bottom: 1px solid #00ff8844; padding-bottom: 0.5rem; }
    pre { background: #111; padding: 1rem; border: 1px solid #333; min-height: 60px; white-space: pre-wrap; word-break: break-all; }
    .error { color: #ff4444; }
    a { color: #00ff88; }
  </style>
</head>
<body>
  <h1>[ Execution Result ]</h1>
  <pre>${error ? `<span class="error">Error: ${escapeHtml(error)}</span>` : escapeHtml(output) || "(no output)"}</pre>
  <a href="/">&#8592; Back</a>
</body>
</html>
  `);
});

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Js listening on :${PORT}`);
});
