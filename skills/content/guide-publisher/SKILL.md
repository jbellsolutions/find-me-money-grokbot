---
name: guide-publisher
description: Choose, write, check and save a guide page on findreferralpartners.com (it appears at /guides/<slug>). Use for the Referral guides run, a question handed over by sales, or when Justin asks for a page, an article, SEO content or what to write next.
---

# Guide publisher

The site makes its own directory pages: every listed business gets `/business/<slug>`, and its state, city, city-plus-category and category pages exist as soon as there is a real listing there (and not before). This skill adds the other kind of page: a guide that answers a question an owner has when they are looking for referral partners.

## Choosing the question

Sources, best first: questions members actually asked (`requests/content/`), what the live search results show people ask around "referral partners", "referral agreement", "referral fee", "cross promotion", "email list swap" for local businesses, and Search Console queries once it is connected. Check `python3 repo/tools/rc.py pages` so no question is answered twice. Record the query, where it was seen and the date in the brief. Search volume is not needed to pick a real question, and none is ever made up.

Starting list, each one a single page:
- How to set a referral commission between two local businesses
- What to put in a referral agreement (the three things to agree before you send)
- How to write a referral email to your customer list (with a worked example)
- Which businesses make good referral partners for a <trade> (one page per trade with listings on the site)
- Referral campaign or networking group: how they differ
- How to track which customers came from a referral partner

## The brief (write it before the draft, in `daily/<date>/content.md`)

Who is asking and at what point; the question in their words; what the page will let them do when they finish it; the facts it needs and where each comes from; which site pages it links to (`/join`, `/directory`, the city or category pages that exist, other guides); what would make it wrong or stale.

## Writing it

- Answer the question in the first paragraph. Then the detail, in short sections with plain headings.
- Every fact is true and has a source in the brief. An example is labelled as an example and uses made-up names. Rules about referral fees differ by profession and place (real estate, law, healthcare, insurance, financial advice): say that the reader should check their own, and link to an authoritative source when one is cited.
- Original writing. Nothing copied, nothing spun from another page.
- Body only: `<h2>`, `<h3>`, `<p>`, `<ul>`, `<ol>`, `<table>`, `<a>`, `<strong>`, `<blockquote>`. The site adds the title (`<h1>`), the layout, the breadcrumb, the Article data and the sign-up buttons, and refuses scripts, iframes and inline handlers.
- Title under 110 characters, in the reader's words. Description under 300, saying what they get.

## Check, save, publish

1. A second pass as a different reader: is every claim true, is the example labelled, does every link resolve (fetch each one), would the page still be useful with the site's name removed.
2. Save as a draft: `rc.py page-put <slug> --title "<title>" --description "<description>" --html <file>`. A draft returns 404 to the public; `rc.py page-get <slug>` reads it back.
3. Publishing is `rc.py page-put ... --publish`. It makes the page public at once at `/guides/<slug>`, adds it to `/guides` and to the sitemap. Run `python3 repo/guards/scripts/send_guard.py rc_guide` first: anything but `auto` means the draft and its brief go to `requests/justin/`.
4. After a publish: fetch the live page, confirm 200 and that it has no `noindex`, and write the link to `requests/outreach/` as something worth sharing.

## Measuring (Fridays)

`rc.py stats` → `by_source` and `by_area` for sign-ups. For each published guide: is it reachable, is it in the sitemap, and (with Search Console) impressions and clicks for the period, with the dates. A fixed panel of ten buyer questions is asked of the AI answer engines the bot can reach, the same wording each time, and the answer, the cited links and whether the site is mentioned are recorded with the date. A failed check is recorded as missing, not as zero.
