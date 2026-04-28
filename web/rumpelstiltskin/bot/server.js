const express = require("express");
const { visit } = require("./bot");

const app = express();
app.use(express.json());
app.use(frameOptionsExcept404);

const PORT = process.env.PORT || 3004;

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

app.get("/", (_req, res) => {
    res.type("html").send(`
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Bot Report</title>
            <style>
                :root {
                    --bg: #07110d;
                    --panel: #0d1a15;
                    --border: #1f3a2d;
                    --text: #d7f5e3;
                    --muted: #87b69b;
                    --accent: #56d39b;
                    --accent2: #f6b26b;
                }
                * { box-sizing: border-box; }
                body {
                    margin: 0;
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    font-family: Arial, Helvetica, sans-serif;
                    color: var(--text);
                    background:
                        radial-gradient(circle at top, rgba(86, 211, 155, 0.14), transparent 35%),
                        linear-gradient(180deg, #07110d 0%, #091712 100%);
                }
                .shell {
                    width: min(720px, calc(100vw - 32px));
                    border: 1px solid var(--border);
                    background: rgba(13, 26, 21, 0.96);
                    box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
                    padding: 28px;
                }
                h1 {
                    margin: 0 0 8px;
                    font-size: 24px;
                    letter-spacing: 0;
                }
                p {
                    margin: 0 0 20px;
                    color: var(--muted);
                    line-height: 1.5;
                }
                label {
                    display: block;
                    margin: 0 0 8px;
                    font-size: 13px;
                    text-transform: uppercase;
                    color: var(--muted);
                }
                input, button {
                    font: inherit;
                }
                input {
                    width: 100%;
                    padding: 12px 14px;
                    border: 1px solid var(--border);
                    background: #08130f;
                    color: var(--text);
                    outline: none;
                }
                input:focus {
                    border-color: var(--accent);
                }
                button {
                    margin-top: 14px;
                    width: 100%;
                    padding: 12px 14px;
                    border: 1px solid var(--accent);
                    background: var(--accent);
                    color: #04120c;
                    font-weight: 700;
                    cursor: pointer;
                }
                button:hover {
                    background: #79e0b2;
                }
                .note {
                    margin-top: 14px;
                    font-size: 13px;
                    color: var(--accent2);
                }
            </style>
        </head>
        <body>
            <main class="shell">
                <h1>Admin Report Console</h1>
                <p>Submit a URL and the bot will visit it in the background.</p>
<form id="reportForm">
    <label for="url">Target URL</label>
    <input id="url" name="url" type="url" placeholder="https://example.com" required />
    <button type="submit">Send to Bot</button>
</form>

<script>
    const form = document.getElementById('reportForm');

    form.addEventListener('submit', async (e) => {
        e.preventDefault(); // Stop the page from refreshing

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/report', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                alert('Report sent successfully!');
            } else {
                alert('Failed to send report.');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    });
</script>
                <div class="note">The JSON API at <code>/report</code> still works.</div>
            </main>
        </body>
        </html>
    `);
});

app.post("/report", async (req, res) => {
    const { url } = req.body;
    if (!url || !url.startsWith("http")) {
        return res.status(400).send("Invalid URL");
    }

    console.log(`[Server] Received report for ${url}`);

    // Run the bot asynchronously so we don't block the request
    visit(url).catch(err => console.error(err));

    res.send("Admin is visiting your URL...");
});

app.listen(PORT, () => {
    console.log(`Bot server listening on :${PORT}`);
});
