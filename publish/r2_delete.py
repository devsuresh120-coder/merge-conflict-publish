"""Delete episode videos from Cloudflare R2.

Reads queue/r2_delete.txt (episode numbers, one per line or ranges like "36-55"),
deletes every object for those episodes in the Merge Conflict folder
(merge-conflict/epNN_<hash>.mp4) and the old bucket root (epNN.mp4), prints what it
deleted, then empties the file. Only this series' objects are touched (never blobby/).

Env (GitHub Secrets): R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET.
Optional: R2_PREFIX (default merge-conflict), DRY_RUN=1.
"""
import os
import re
import sys

import boto3

LIST = os.path.join(os.path.dirname(__file__), "..", "queue", "r2_delete.txt")
DRY = os.environ.get("DRY_RUN") == "1"


def episodes():
    eps = set()
    if not os.path.exists(LIST):
        return eps
    for ln in open(LIST):
        ln = ln.split("#")[0].strip()
        if not ln:
            continue
        if "-" in ln:
            a, b = ln.split("-")
            eps.update(range(int(a), int(b) + 1))
        else:
            eps.add(int(ln))
    return eps


def main():
    eps = episodes()
    if not eps:
        print("queue/r2_delete.txt is empty: nothing to delete")
        return
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    bucket = os.environ["R2_BUCKET"]
    prefix = os.environ.get("R2_PREFIX", "merge-conflict").strip("/")
    pat = re.compile(rf"^(?:{re.escape(prefix)}/)?ep(\d+)(?:_[0-9a-f]+)?\.(?:mp4|jpg|png)$")
    doomed = []
    for pfx in (f"{prefix}/ep", "ep"):
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=pfx):
            for obj in page.get("Contents", []):
                m = pat.match(obj["Key"])
                if m and int(m.group(1)) in eps:
                    doomed.append(obj["Key"])
    print(f"Episodes {sorted(eps)}: {len(doomed)} object(s) in R2")
    for key in doomed:
        if DRY:
            print("  [dry] would delete", key)
        else:
            s3.delete_object(Bucket=bucket, Key=key)
            print("  deleted", key)
    if not DRY:
        open(LIST, "w").write("# Episodes to delete from R2 (e.g. 36-55). Emptied after each run.\n")


if __name__ == "__main__":
    sys.exit(main())
