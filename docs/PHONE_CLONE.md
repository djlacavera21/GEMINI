# Owner-authorized phone clone

GEMINI will not silently copy a phone. A live clone requires all of:

1. The phone on USB.
2. Android "Allow USB debugging" / RSA fingerprint, or iPhone "Trust This Computer".
3. A short-lived owner-consent job bound to that serial, scope, operator session, and expiry.
4. The owner opening the SMS (or printed) link on the phone and approving it.
5. Optional platform passkey on that phone, which signs the job challenge.
6. An explicit `--live` flag. The default is dry-run.

The SMS body is only an approval URL. The passkey never leaves the phone. The link is not a clone command and not a login code.

## Command line

```bash
gemini-cloner                 # interactive menu
gemini-cloner phone detect
gemini-cloner phone serve
gemini-cloner phone request --phone +15555550100 --scope media,documents,packages
gemini-cloner phone status <job_id>
gemini-cloner phone clone <job_id>          # dry-run
gemini-cloner phone clone <job_id> --live   # actually pull
```

If the consent page must be opened off-LAN, put a tunnel URL in `GEMINI_PUBLIC_BASE_URL` and restart `phone serve` behind that tunnel.

## What "full clone" means here

It does **not** mean:

- bypassing a lock screen
- cloning a phone that is not physically trusted
- decrypting an iOS backup without the owner password
- reading SMS without an on-device export path
- installing spyware, using exploits, or ignoring `unauthorized` adb state

It **does** mean: after the owner consents and taps the OS trust prompt, copy the requested scoped data with stock `adb` / `idevicebackup2`.

## SMS

Optional. Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`. Otherwise print the link and send it yourself.
