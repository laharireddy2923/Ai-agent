import subprocess
import time
import re
import sys

print("Starting persistent zero-click tunnel for http://127.0.0.1:5005 ...")

proc = subprocess.Popen('ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=5 -R 80:localhost:5005 nokey@localhost.run', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

url = None
for _ in range(40):
    line = proc.stdout.readline()
    if line:
        print(line, end='')
        match = re.search(r'https://[a-zA-Z0-9-]+\.lhr\.life', line)
        if match:
            url = match.group(0)
            print(f"\nDIRECT_URL: {url}\n")
            with open('direct_url.txt', 'w') as f:
                f.write(url)
            sys.stdout.flush()
            break

if not url:
    print("Could not parse direct URL")

while True:
    time.sleep(10)
