# Owner-authorized phone clone

GEMINI will not silently copy a phone. A live clone requires all of:

1. A trusted transport: USB, or wifi/remote after that same OS trust already exists.
2. Android "Allow USB debugging" / RSA fingerprint, or iPhone "Trust This Computer". Wireless debugging pairing code if the operator is off-cable.
3. A short-lived owner-consent job bound to that serial, scope, operator session, transport, and expiry.
4. The owner opening the SMS (or printed) link on the phone and approving it.
5. Optional platform passkey on that phone, which signs the job challenge.
6. An explicit `--live` flag. The default is dry-run.

The SMS body is only an approval URL. The passkey never leaves the phone. The link is not a clone command and not a login code.

## USB

```bash
gemini-cloner phone detect
gemini-cloner phone request --transport usb --phone +15555550100 --scope media,documents,packages
gemini-cloner phone clone <job_id> --live
```

## Remote / wifi

Only after OS trust already exists. Two legal paths:

1. USB first, flip the authorized device to TCP, unplug, connect by IP:
```bash
gemini-cloner phone transport tcpip --port 5555
gemini-cloner phone transport connect --host 10.0.0.20 --port 5555
gemini-cloner phone request --transport wifi --phone +15555550100 --serial 10.0.0.20:5555
```

2. Android 11+ wireless debugging. Owner shows the pairing code on the phone:
```bash
gemini-cloner phone transport pair --host 10.0.0.20 --port 37123 --code 123456
gemini-cloner phone transport connect --host 10.0.0.20 --port 5555
```

`remote` is wifi plus the public consent URL. It is not a backdoor. GEMINI will not pair without the on-phone code, will not talk to an unauthorized device, and will not install an agent.

If the consent page must be opened off-LAN, set `GEMINI_PUBLIC_BASE_URL` to a tunnel in front of `phone serve`.

## What this is not

- lock-screen bypass
- cloning a phone that is not trusted
- silent internet implant
- decrypting an iOS backup without the owner password
- ignoring `unauthorized` adb state
