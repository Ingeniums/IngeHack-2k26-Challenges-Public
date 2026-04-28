const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

loadEnvFile(path.join(__dirname, ".env"));

const PORT = Number.parseInt(process.env.PORT || "3000", 10);
const HOST = process.env.HOST || "127.0.0.1";
const GOOGLE_APPS_SCRIPT_URL = process.env.GOOGLE_APPS_SCRIPT_URL || "";
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || "*";
const FRONTEND_DIR = path.resolve(__dirname, "../frontend");
const REQUIRED_FIELDS = [
  "firstName",
  "lastName",
  "email",
  "phone",
  "dateOfBirth",
  "address",
];
const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
};

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return;
  }

  const fileContents = fs.readFileSync(filePath, "utf8");

  for (const rawLine of fileContents.split(/\r?\n/)) {
    const line = rawLine.trim();

    if (!line || line.startsWith("#")) {
      continue;
    }

    const separatorIndex = line.indexOf("=");

    if (separatorIndex === -1) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();

    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key) || process.env[key]) {
      continue;
    }

    let value = line.slice(separatorIndex + 1).trim();

    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    process.env[key] = value;
  }
}

function setCorsHeaders(response) {
  response.setHeader("Access-Control-Allow-Origin", ALLOWED_ORIGIN);
  response.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  response.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

function sendJson(response, statusCode, payload) {
  setCorsHeaders(response);
  response.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
  });
  response.end(JSON.stringify(payload));
}

function sendFile(response, statusCode, fileContents, filePath) {
  response.writeHead(statusCode, {
    "Content-Type":
      MIME_TYPES[path.extname(filePath).toLowerCase()] ||
      "application/octet-stream",
  });
  response.end(fileContents);
}

function sanitize(value) {
  return value === null || value === undefined ? "" : String(value).trim();
}

function normalizePayload(payload) {
  return {
    firstName: sanitize(payload.firstName),
    lastName: sanitize(payload.lastName),
    email: sanitize(payload.email),
    phone: sanitize(payload.phone),
    dateOfBirth: sanitize(payload.dateOfBirth),
    address: sanitize(payload.address),
  };
}

function validatePayload(payload) {
  const missingFields = REQUIRED_FIELDS.filter((field) => !payload[field]);

  if (missingFields.length > 0) {
    const error = new Error(
      `Missing required fields: ${missingFields.join(", ")}.`,
    );
    error.statusCode = 400;
    throw error;
  }

  if (!GOOGLE_APPS_SCRIPT_URL) {
    const error = new Error(
      "Set GOOGLE_APPS_SCRIPT_URL before starting the backend.",
    );
    error.statusCode = 500;
    throw error;
  }
}

function readJsonBody(request) {
  return new Promise((resolve, reject) => {
    let body = "";

    request.on("data", (chunk) => {
      body += chunk;

      if (body.length > 1_000_000) {
        const error = new Error("Request body too large.");
        error.statusCode = 413;
        reject(error);
        request.destroy();
      }
    });

    request.on("end", () => {
      if (!body) {
        resolve({});
        return;
      }

      try {
        resolve(JSON.parse(body));
      } catch (error) {
        const parseError = new Error("Invalid JSON body.");
        parseError.statusCode = 400;
        reject(parseError);
      }
    });

    request.on("error", (error) => {
      error.statusCode = error.statusCode || 400;
      reject(error);
    });
  });
}

async function readForwardResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch (error) {
      return null;
    }
  }

  const text = await response.text();
  return text ? { message: text } : null;
}

async function forwardToAppsScript(payload) {
  let forwardResponse;

  try {
    forwardResponse = await fetch(GOOGLE_APPS_SCRIPT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    const networkError = new Error(
      `Could not reach Google Apps Script: ${error.message}`,
    );
    networkError.statusCode = 502;
    throw networkError;
  }

  const result = await readForwardResponse(forwardResponse);

  if (!forwardResponse.ok) {
    const error = new Error(
      result?.message ||
        `Google Apps Script returned ${forwardResponse.status}.`,
    );
    error.statusCode = 502;
    throw error;
  }

  if (result && typeof result === "object" && result.ok === false) {
    const error = new Error(
      result.message || "Google Apps Script rejected the submission.",
    );
    error.statusCode = 502;
    throw error;
  }

  return result;
}

async function serveFrontendAsset(requestPath, response) {
  const safePath = requestPath === "/" ? "/index.html" : requestPath;
  const decodedPath = decodeURIComponent(safePath);
  const filePath = path.resolve(FRONTEND_DIR, `.${decodedPath}`);

  if (
    filePath !== FRONTEND_DIR &&
    !filePath.startsWith(`${FRONTEND_DIR}${path.sep}`)
  ) {
    sendJson(response, 404, {
      ok: false,
      message: "Not found.",
    });
    return true;
  }

  try {
    const fileContents = await fs.promises.readFile(filePath);
    sendFile(response, 200, fileContents, filePath);
    return true;
  } catch (error) {
    if (error.code === "ENOENT" || error.code === "EISDIR") {
      return false;
    }

    sendJson(response, 500, {
      ok: false,
      message: "Could not load frontend asset.",
    });
    return true;
  }
}

const server = http.createServer(async (request, response) => {
  const requestUrl = new URL(
    request.url || "/",
    `http://${request.headers.host || "localhost"}`,
  );

  if (request.method === "OPTIONS") {
    setCorsHeaders(response);
    response.writeHead(204);
    response.end();
    return;
  }

  if (request.method === "GET" && requestUrl.pathname === "/health") {
    sendJson(response, 200, {
      ok: true,
      message: "Registration backend is running.",
    });
    return;
  }

  if (request.method === "POST" && requestUrl.pathname === "/api/register") {
    try {
      const payload = normalizePayload(await readJsonBody(request));
      validatePayload(payload);

      const result = await forwardToAppsScript(payload);

      sendJson(response, 200, {
        ok: true,
        message:
          result?.message || "Registration forwarded to Google Apps Script.",
      });
    } catch (error) {
      sendJson(response, error.statusCode || 500, {
        ok: false,
        message: error.message || "Registration failed.",
      });
    }
    return;
  }

  if (request.method === "GET") {
    const served = await serveFrontendAsset(requestUrl.pathname, response);

    if (served) {
      return;
    }
  }

  sendJson(response, 404, {
    ok: false,
    message: "Not found.",
  });
});

server.listen(PORT, HOST, () => {
  console.log(`Registration backend listening on http://${HOST}:${PORT}`);
});
