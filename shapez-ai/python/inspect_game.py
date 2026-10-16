import json
import urllib.request
import sys

def eval_rpc(code_str):
    payload = json.dumps({"action": "eval_code", "params": {"code": code_str}}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:8765/api/rpc", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "return { ready: true };"
    res = eval_rpc(code)
    print(json.dumps(res, indent=2, ensure_ascii=False))
