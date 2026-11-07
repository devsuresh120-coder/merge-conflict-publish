"""Print the Buffer account, organizations and connected channels (token check)."""
import os, json, requests
H = {"Authorization": "Bearer " + os.environ["BUFFER_ACCESS_TOKEN"]}
API = "https://api.buffer.com"
a = requests.post(API, json={"query": "{ account { id email organizations { id name } } }"}, headers=H, timeout=60).json()
print(json.dumps(a, indent=1))
for o in a.get("data", {}).get("account", {}).get("organizations", []):
    c = requests.post(API, json={"query": "query($o:OrganizationId!){ channels(input:{organizationId:$o}){ id name service } }",
                                 "variables": {"o": o["id"]}}, headers=H, timeout=60).json()
    print(json.dumps(c, indent=1))
