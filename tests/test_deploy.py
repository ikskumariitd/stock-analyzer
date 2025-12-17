import urllib.request
import sys

def verify_deploy():
    url = "https://stock-analyzer-641888119120.us-central1.run.app"
    try:
        print(f"Checking {url}...")
        resp = urllib.request.urlopen(url)
        print(f"Status: {resp.status}")
        if resp.status == 200:
            print("SUCCESS: Service is reachable.")
        else:
            print(f"FAILURE: Status {resp.status}")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    verify_deploy()
