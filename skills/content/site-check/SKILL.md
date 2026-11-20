---
name: site-check
description: The daily read-only health check of findreferralpartners.com. Use in the Weekly AEO read and the Referral guides run or when Justin asks whether the site is up, what is indexed, or why a page is missing.
---

# Site check

Read-only. Nothing here changes the site.

1. `GET /api/health` returns `{"ok": true, ...}` with the listing count. Anything else is an alarm to Slack and a note in `requests/justin/`.
2. `GET /sitemap.xml`, then fetch every URL in it (the usage script `retry.py` for flaky calls). Each returns 200 and carries no `noindex`. Record the count and any that fail.
3. `python3 repo/tools/rc.py listings`: every listing's `/business/<slug>`, state page and city page is in the sitemap.
4. `python3 repo/tools/rc.py pages`: every row with `published` 0 returns 404 without the key (a draft that is public is an alarm).
5. `GET /robots.txt` allows `/` and names the sitemap.
6. Home page: the title, the description, one `<h1>`, the FAQ data, and the sign-up form are present (`clean_page.py`, then `grep_lines.sh`).
7. `/directory/zz` (an area with no listings) returns 404: the site has not started making empty area pages.

Write `daily/<date>/content.md`: URLs in the sitemap, URLs failing, drafts, listings. A site fault is not this bot's to fix: the code lives in Justin's private repo, so it goes to `requests/justin/` with the URL, what was expected and what came back.
