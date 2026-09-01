from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from gemini_cloner.consent import approve_job, decode_client_data, deny_job, verify_token, ConsentError

PAGE = """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"/><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>
<title>GEMINI owner consent</title>
<style>body{font-family:system-ui;background:#0b1210;color:#e8f0e6;margin:0}main{max-width:36rem;margin:2rem auto;padding:1.5rem;background:#15201b;border:1px solid #2c4a3c;border-radius:16px}button{font:inherit;padding:.7rem 1rem;margin:.3rem .3rem 0 0;border-radius:10px;border:0;cursor:pointer}.go{background:#3d7a55;color:#fff}.no{background:#7a3d3d;color:#fff}.muted{color:#9bb5a6}</style></head>
<body><main>
<h1>GEMINI phone-clone consent</h1>
<p class=\"muted\">SMS is only this approval page. USB trust is still required. The passkey stays on the phone.</p>
<pre id=\"job\"></pre>
<p><button class=\"go\" id=\"passkey\">Approve with passkey on this phone</button>
<button class=\"go\" id=\"confirm\">Approve this job</button>
<button class=\"no\" id=\"deny\">Deny</button></p>
<p id=\"out\" class=\"muted\"></p>
</main>
<script>
const params=new URLSearchParams(location.search);
const jobId=params.get('job'); const token=params.get('token');
function b64url(buf){const bytes=buf instanceof ArrayBuffer?new Uint8Array(buf):buf;let str=btoa(String.fromCharCode(...bytes));return str.replaceAll('+','-').replaceAll('/','_').replaceAll('=','');}
async function loadJob(){const res=await fetch('/api/job?job='+encodeURIComponent(jobId)+'&token='+encodeURIComponent(token)); const data=await res.json(); document.getElementById('job').textContent=JSON.stringify(data,null,2); return data;}
async function post(path,body){const res=await fetch(path,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)}); const data=await res.json(); document.getElementById('out').textContent=JSON.stringify(data,null,2); return data;}
document.getElementById('confirm').onclick=()=>post('/api/approve',{job:jobId,token,method:'owner-confirm',note:'SMS link opened and confirmed on phone'});
document.getElementById('deny').onclick=()=>post('/api/deny',{job:jobId,token,reason:'owner denied'});
document.getElementById('passkey').onclick=async()=>{
  const job=await loadJob();
  if(!window.PublicKeyCredential){document.getElementById('out').textContent='Passkey API not available; use Approve this job.';return;}
  const challenge=new TextEncoder().encode(job.challenge);
  const cred=await navigator.credentials.create({publicKey:{challenge,rp:{name:'GEMINI Cloner',id:location.hostname},user:{id:new TextEncoder().encode(job.job_id),name:job.phone||'owner',displayName:'Device owner'},pubKeyCredParams:[{type:'public-key',alg:-7},{type:'public-key',alg:-257}],authenticatorSelection:{authenticatorAttachment:'platform',userVerification:'required'},timeout:120000}});
  const clientData=JSON.parse(new TextDecoder().decode(cred.response.clientDataJSON));
  await post('/api/approve',{job:jobId,token,method:'passkey',credential_id:b64url(cred.rawId),client_data:clientData,note:'platform passkey signed job challenge on owner phone'});
};
loadJob().catch(err=>{document.getElementById('out').textContent=String(err);});
</script></body></html>
"""


def make_handler(root: Path):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, code: int, payload: dict) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _html(self, code: int, body: str) -> None:
            raw = body.encode("utf-8")
            self.send_response(code)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/approve":
                self._html(200, PAGE)
                return
            if parsed.path == "/api/job":
                qs = parse_qs(parsed.query)
                try:
                    job = verify_token(root, qs.get("job", [""])[0], qs.get("token", [""])[0])
                except ConsentError as exc:
                    self._json(400, {"error": str(exc)})
                    return
                self._json(200, {"job_id": job["job_id"], "status": job["status"], "phone": job["phone"], "platform": job["platform"], "serial": job["serial"], "scope": job["scope"], "expires_at": job["expires_at"], "operator": job["operator"], "challenge": job["challenge"]})
                return
            self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            length = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid json"})
                return
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/approve":
                    client_data = body.get("client_data")
                    if isinstance(body.get("client_data_json"), str):
                        client_data = decode_client_data(body["client_data_json"])
                    job = approve_job(root, body.get("job", ""), body.get("token", ""), method=body.get("method") or "owner-confirm", client_data=client_data, credential_id=body.get("credential_id"), note=body.get("note") or "")
                    self._json(200, {"status": job["status"], "job_id": job["job_id"], "approved_at": job.get("approved_at")})
                    return
                if parsed.path == "/api/deny":
                    job = deny_job(root, body.get("job", ""), body.get("token", ""), body.get("reason") or "denied")
                    self._json(200, {"status": job["status"], "job_id": job["job_id"]})
                    return
            except ConsentError as exc:
                self._json(400, {"error": str(exc)})
                return
            self._json(404, {"error": "not found"})

    return Handler


def serve(root: Path, host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(root))
