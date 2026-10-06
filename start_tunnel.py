import subprocess
import time
import re
import sys

print("Starting public tunnel for http://127.0.0.1:5005 ...")

# Try localtunnel
try:
    proc = subprocess.Popen('npx --yes localtunnel --port 5005', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(5)
    for _ in range(10):
        line = proc.stdout.readline()
        if 'your url is:' in line.lower() or 'loca.lt' in line:
            url = line.strip().split()[-1]
            print(f"PUBLIC_URL: {url}")
            with open('public_url.txt', 'w') as f:
                f.write(url)
            sys.stdout.flush()
            break
except Exception as e:
    print("Localtunnel error:", e)

while True:
    time.sleep(30)
