const CONFIG = {
  sheetName: "Main",
  headers: [
    "Timestamp",
    "First Name",
    "Last Name",
    "Email",
    "Phone",
    "Date of Birth",
    "Address",
  ],
};

function doGet() {
  return jsonResponse_({
    ok: true,
    message: "Apps Script sheet writer is running.",
  });
}

function doPost(e) {
  const lock = LockService.getScriptLock();

  try {
    lock.waitLock(30000);

    const payload = normalizePayload_(parsePayload_(e));
    validatePayload_(payload);

    const sheet = getOrCreateSheet_();
    sheet.appendRow([
      new Date(),
      payload.firstName,
      payload.lastName,
      payload.email,
      payload.phone,
      payload.dateOfBirth,
      payload.address,
    ]);

    return jsonResponse_({
      ok: true,
      message: "Registration saved.",
    });
  } catch (error) {
    return jsonResponse_({
      ok: false,
      message: error.message,
    });
  } finally {
    if (lock.hasLock()) {
      lock.releaseLock();
    }
  }
}

function parsePayload_(e) {
  if (e && e.postData && e.postData.contents) {
    try {
      return JSON.parse(e.postData.contents);
    } catch (error) {
      return e.parameter || {};
    }
  }

  return (e && e.parameter) || {};
}

function normalizePayload_(payload) {
  return {
    firstName: sanitize_(payload.firstName),
    lastName: sanitize_(payload.lastName),
    email: sanitize_(payload.email),
    phone: sanitize_(payload.phone),
    dateOfBirth: sanitize_(payload.dateOfBirth),
    address: sanitize_(payload.address),
  };
}

function validatePayload_(payload) {
  if (
    !payload.firstName ||
    !payload.lastName ||
    !payload.email ||
    !payload.phone ||
    !payload.dateOfBirth ||
    !payload.address
  ) {
    throw new Error("Missing required registration fields.");
  }
}

function getOrCreateSheet_() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();

  if (!spreadsheet) {
    throw new Error(
      "This Apps Script must be bound to the target Google Sheet.",
    );
  }

  let sheet = spreadsheet.getSheetByName(CONFIG.sheetName);

  if (!sheet) {
    sheet = spreadsheet.insertSheet(CONFIG.sheetName);
  }

  if (sheet.getLastRow() === 0) {
    sheet.appendRow(CONFIG.headers);
  }

  return sheet;
}

function sanitize_(value) {
  return value === null || value === undefined ? "" : String(value).trim();
}

function jsonResponse_(payload) {
  return ContentService.createTextOutput(JSON.stringify(payload)).setMimeType(
    ContentService.MimeType.JSON,
  );
}
