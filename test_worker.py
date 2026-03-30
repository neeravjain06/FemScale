import requests
import time

codes = {
    "O(1)": """
def handler(event):
    return {"status": "ok", "ping": "pong"}
""",
    "O(n)": """
def handler(event):
    arr = list(range(100000))
    s = sum(arr)
    return {"sum": s}
""",
    "O(n²)": """
def handler(event):
    arr = list(range(2000))
    count = 0
    for i in arr:
        for j in arr:
            count += 1
    return {"count": count}
"""
}

def test():
    for complexity, code in codes.items():
        print(f"\\n--- Testing {complexity} ---")
        res = requests.post("http://localhost:8000/v1/jobs", json={"code": code})
        job_id = res.json().get("job_id")
        
        while True:
            res = requests.get(f"http://localhost:8000/v1/jobs/{job_id}").json()
            if res.get("status") in ["success", "failed", "timeout"]:
                print(f"   Status: {res['status']}")
                print(f"   Detected Complexity: {res.get('complexity')}")
                print(f"   Memory: {res.get('memory_mb')} MB")
                print(f"   Time:   {res.get('duration_ms')} ms")
                break
            time.sleep(0.5)

if __name__ == "__main__":
    test()
