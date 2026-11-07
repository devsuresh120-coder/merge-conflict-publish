"""Move Shorts that are already waiting in Buffer to the time now written in schedule.csv.

Buffer's API has no 'change time' call we rely on, so for every still-scheduled post whose
time differs from schedule.csv we delete it in Buffer and drop it from posted.json; the normal
publish run right after re-creates it at the new time. Posts that already went out are never touched.
Run with workflow_dispatch action=reschedule.
"""
import csv, datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import publish as P


def note(t, m):
    print(f"::notice title={t}::" + str(m).replace("\n", " ")[:1500])


def delete_mutation():
    t = P.gql('query{ __type(name:"Mutation"){ fields{ name args{ name type{ name kind ofType{ name } } } } } }')["__type"]
    names = {f["name"]: f for f in t["fields"]}
    note("post mutations", [n for n in names if "post" in n.lower()])
    f = names.get("deletePost")
    if not f:
        sys.exit("Buffer API has no deletePost mutation; reschedule by hand in Buffer")
    arg = f["args"][0]
    tname = arg["type"]["name"] or (arg["type"]["ofType"] or {}).get("name")
    fields = []
    if tname:
        it = P.gql('query($n:String!){ __type(name:$n){ inputFields{ name } } }', {"n": tname})["__type"]
        fields = [x["name"] for x in (it or {}).get("inputFields") or []]
    note("deletePost", f"arg {arg['name']}: {tname} {fields}")
    return arg["name"], tname, fields


def main():
    rows = {f"{r['episode']}:{r['platform'].lower()}": r for r in csv.DictReader(open("queue/schedule.csv"))}
    posted = json.load(open("queue/posted.json"))
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    todo = []
    for key, v in posted.items():
        r = rows.get(key)
        if not r or not v.get("post_id") or v.get("manual") or v.get("via", "buffer") != "buffer":
            continue
        want = P.due_iso(r["due_at"]) if r.get("due_at", "").strip() else None
        if not want:
            continue
        have = v.get("due_at") or ""
        if have and have > now and want != have:
            todo.append((key, v["post_id"], have, want))
    note("to move", [(k, h, w) for k, _, h, w in todo])
    if not todo or os.environ.get("DRY_RUN") == "1":
        return
    argname, tname, fields = delete_mutation()
    idfield = "id" if "id" in fields else (fields[0] if fields else None)
    q = ('mutation($i:%s!){ deletePost(%s:{%s:$i}){ __typename ... on MutationError { message } } }' % (tname, argname, idfield)) if idfield \
        else ('mutation($i:PostId!){ deletePost(%s:$i){ __typename ... on MutationError { message } } }' % argname)
    for key, pid, have, want in todo:
        st = P.gql('query($i:PostId!){ post(input:{id:$i}){ status } }', {"i": pid})["post"]["status"]
        if st != "scheduled":
            note("skip " + key, f"status {st}")
            continue
        try:
            if idfield:
                q2 = 'mutation($i:PostId!){ deletePost(%s:{%s:$i}){ __typename ... on MutationError { message } } }' % (argname, idfield)
                res = P.gql(q2, {"i": pid})
            else:
                res = P.gql(q, {"i": pid})
            note("deleted " + key, json.dumps(res))
            if "MutationError" in json.dumps(res):
                continue
            posted.pop(key, None)
        except Exception as e:
            note("delete failed " + key, e)
    json.dump(posted, open("queue/posted.json", "w"), indent=1)


main()
