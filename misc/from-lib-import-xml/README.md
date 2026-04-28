# Registration Form + Node Proxy Backend

This project contains:

- `frontend/`: a static registration page
- `backend/`: a Node API that accepts the form request and forwards it to Google Apps Script
- `backend/apps-script/`: the Google Apps Script that writes submissions into a Google Sheet

## 1. Set up the Google Sheet and Apps Script

Create the Google Sheet you want to write to.

1. Open Google Apps Script.
2. Create a new Apps Script project.
3. Copy the contents of `backend/apps-script/Code.gs` and `backend/apps-script/appsscript.json` into that project.
4. Bind the Apps Script project to the Google Sheet you want to write to.
5. Deploy the script as a web app:
   - Execute as: `Me`
   - Who has access: `Anyone`
6. Copy the deployed web app URL.

## 2. Start the Node backend

The backend loads `backend/.env` automatically. This file is backend-only.

Example `backend/.env`:

```dotenv
HOST=127.0.0.1
PORT=3000
GOOGLE_APPS_SCRIPT_URL=https://script.google.com/macros/s/your-deployment-id/exec
ALLOWED_ORIGIN=*
```

Then start the server:

```bash
cd backend
npm start
```

Optional environment variables:

- `HOST`: bind address, default `127.0.0.1`
- `PORT`: API port, default `3000`
- `ALLOWED_ORIGIN`: CORS origin, default `*`

There are no runtime dependencies, so `npm install` is not required.

## 3. Configure the frontend

The frontend is served by the Node backend and uses the same origin by default:

```js
window.APP_CONFIG = {
  apiUrl: "/api/register",
};
```

The frontend does not need `GOOGLE_APPS_SCRIPT_URL`. Put that variable only in `backend/.env`.

## 4. Run the frontend

Start the backend, then open `http://localhost:3000`.

## Notes

- The Node backend endpoint is `POST /api/register`.
- The Node backend also serves the static frontend from the same port.
- The Node backend forwards the JSON payload to the deployed Google Apps Script URL.
- The Apps Script writes into the bound spreadsheet and uses the `Main` sheet.
- The header row is created automatically on the first successful submission.
