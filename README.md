# merge-conflict-publish

Publisher code for the *Merge Conflict* series (public). It holds **no data**: the schedule, captions, videos,
post kits, studio files and logs live in the owner's **private** `social-hub` repo under `data/merge-conflict/`.

- `publish/publish.py` — uploads each due video to Cloudflare R2 and creates the posts in Buffer (run from the data folder).
- `.github/workflows/publish.yml` — twice a day (and on demand) checks out `social-hub` with `HUB_TOKEN`, runs the
  publisher there and saves `queue/posted.json` + a private log back to `social-hub`. Public run logs show only "ok"/"failed".
- `.github/workflows/r2-delete.yml` — on demand: deletes the episodes listed in `data/merge-conflict/queue/r2_delete.txt`.

Secrets: `HUB_TOKEN` (fine-grained token, only `social-hub`, Contents read/write), `BUFFER_ACCESS_TOKEN`,
`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_URL`.
