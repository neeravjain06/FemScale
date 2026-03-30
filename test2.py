import requests
import time

c = """def handler(event):
    arr = list(range(10000))
    s = sum(arr)
    return {"sum": s}"""

try:
    res = requests.post("http://localhost:8000/v1/jobs", json={"code": c})
    job_id = res.json()["job_id"]
    while True:
        r = requests.get(f"http://localhost:8000/v1/jobs/{job_id}").json()
        if r["status"] in ["success", "failed"]:
            print("Status: ", r["status"])
            print("Error: ", r.get("error"))
            print("Memory: ", r.get("memory_mb"))
            print("Duration: ", r.get("duration_ms"))
            print("Complexity: ", r.get("complexity"))
            break
        time.sleep(0.5)
except Exception as e:
    print(e)
