# Lost Email writeup

## Run locally

```sh
docker compose up --build
```

The challenge listens on:

```text
http://127.0.0.1:9696/
```

## Goal

Get access to the profile page and read the secret flag.

## Solve steps

1. Enter login page
2. Inspect the login page source.

Inside the HTML, there are commented-out input fields. These credentials were left behind during development and testing:

```text
user: koyphshi@ingenieums.club
pass: anti_ai_human
```

3. Log in with those credentials.

After the password is accepted, the app redirects to `/verify` and asks for an email code. At this point, it looks like the login is protected by a second verification step.

4. Do not submit an email code.

Instead, manually visit:

```text
http://127.0.0.1:9696/profile
```

This tests whether the app only hides the profile in the UI, or whether the server actually blocks access until email verification is complete.

5. Gongrats you're on the profile page with the flag

## Why it works

The app sets a valid session immediately after the password login:

```text
session["user"] = username
session["mfa_pending"] = True
session["mfa_verified"] = False
```

The `/profile` route only checks whether a user exists in the session. It does not require `mfa_verified` to be true, so the profile can be opened while email verification is still pending.

Expected flag:

```text
ingehack{y3aH_1T_was_4$_$1MPL3_As_YOU_TH0uGhT}
```
