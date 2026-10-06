import subprocess
import time
import re
import sys

print("Starting Cloudflare Public Tunnel for http://127.0.0.1:5005 ...")

proc = subprocess.Popen('npx --yes @cloudflare/cloudflared tunnel --url http://127.0.0.1:5005', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

time.sleep(6)
for _ in range(30):
    line = proc.stdout.readline()
    print(line, end='')
    if 'trycloudflare.com' in line:
        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if match:
            url = match.group(0)
            print(f"\nCLOUDFLARE_URL: {url}\n")
            with open('cf_url.txt', 'w') as f:
                f.write(url)
            sys.stdout.flush()
            break

while True:
    time.sleep(30)
