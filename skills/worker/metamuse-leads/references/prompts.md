# Muse lead prompts (paste with `muse.py ask --marker <ID>`)

Every prompt starts with the **READ-ONLY HEADER** and ends with the **LEAD ROW** format, so `muse_to_radar.py` can parse the answer. `ask --marker` adds the BEGIN/END lines itself. Swap `{…}` for real values.

## READ-ONLY HEADER (always first)

```text
READ ONLY. Do NOT post, comment, reply, react, message, follow, join, like, save, or write to HighLevel, Slack, ClickUp or any sheet, and do not create, change or delete scheduled tasks. If any step would need an approval, skip it and say which step.
```

## LEAD ROW format (always last)

```text
Output one lead per line, no table, no bullets, no numbering, exactly 9 fields separated by " | ". Never use the "|" character inside a field (write "/" instead), and leave a field empty rather than dropping it:
platform | source | posted_at (YYYY-MM-DD) | url (the post or comment permalink) | author display name | need (one line, their words summarized) | category (starts with real-estate, small-business, trucking, creator, gig or credit, then /subtype) | fit (high, medium or low) | quote (their exact words, max 200 chars)
high = they ask for money now (loan, investor, LOC, financing, partner with capital) with an amount, deal or timeline.
medium = they ask for money with no specifics, or they're about to need it (a deal, an expansion, a bad-credit question).
low = a prospect with no ask yet (an active dealer, contractor, creator or partner).
Skip consumer loans, crypto, MLM, scams, and anyone who is selling funding.
After the rows, one line starting "Tools used:" naming the tools, and whether any approval was asked.
```

---

## FB-1 · Funding asks in my groups (the core sweep)

```text
{READ-ONLY HEADER}
Using your Facebook connector, read the newest posts and their comments from the last {48} hours in every Facebook group I belong to that is about business funding, small business, real-estate investing, trucking, contractors, ecommerce, creators or gig work. Find every post or comment where a person asks for business funding, a business loan, a line of credit, equipment or inventory financing, a hard-money or DSCR lender, or an investor or partner with capital. Max {40} rows, strongest first.
{LEAD ROW format}
```

## FB-2 · One group by link (when group search fails)

```text
{READ-ONLY HEADER}
Open this Facebook group: {group URL}. Read its {30} newest posts and the comments under each. List every funding ask as above.
{LEAD ROW format}
```

## FB-3 · Comment mining on a hot post

```text
{READ-ONLY HEADER}
Read every comment and reply on {post URL}. List each commenter who asks for funding, says they need capital, or asks "who can help with…" for money. Use the comment permalink as url when you have it; otherwise use the post URL and put the comment's first words in quote.
{LEAD ROW format}
```

## FB-4 · Marketplace dealers and high-ticket sellers (prospects)

```text
{READ-ONLY HEADER}
On Facebook Marketplace near {city, ST}, look at {Vehicles / Trailers / Heavy equipment / RVs}. Find business sellers, not one-off sellers: stock numbers, dealer or manufacturer language, several listings from the same seller, a shop address or hours, or $1/FREE placeholder prices. For each seller, give the seller profile URL and count their active listings in need. These are prospects: fit low unless they say they need financing.
{LEAD ROW format}
```

## FB-5 · Partner finder (lenders, brokers, coaches who post deals)

```text
{READ-ONLY HEADER}
In my funding and real-estate groups from the last {7} days, find people who LEND or broker (hard-money lenders, private lenders, DSCR brokers) and coaches or agencies whose clients need funding. These are partners, not borrowers: fit low, category credit/partner or real-estate/partner, and need = what they offer.
{LEAD ROW format}
```

## IG-1 · Instagram asks (bonus channel)

```text
{READ-ONLY HEADER}
Using your Instagram connector, read recent public posts and their comments for {#businessfunding #smallbusinessloan #hardmoneylender #realestateinvesting #fixandflip #truckingbusiness}, plus the comments on my own recent posts. List people asking for funding as above (platform instagram, url = post permalink). If hashtag or comment reading is not available, say exactly what you can read.
{LEAD ROW format}
```

## IG-2 · Creator and partner list

```text
{READ-ONLY HEADER}
From Instagram, list up to {20} accounts that post about business funding, credit, real-estate deals or trucking finance with an engaged audience (comments asking questions). Partners: fit low, category creator/funding-educator, need = their niche and audience size if visible.
{LEAD ROW format}
```

## TK-1 · TikTok (later; no connector)

Muse has no TikTok connector. Its built-in **Browser** connector can open public pages, but this is untested and TikTok often walls logged-out views. Test it once, read-only:

```text
{READ-ONLY HEADER}
With your Browser connector only (no sign-in, no saved credentials), open https://www.tiktok.com/tag/businessfunding and tell me whether you can read video captions and comments. If you can, list up to 10 videos whose comments contain funding asks.
{LEAD ROW format}
```

## REPLY-DRAFT · Drafts for a person to post (never sent by Muse)

```text
{READ-ONLY HEADER}
For each lead below, draft one public reply. Rules: 85 words or fewer; one or two useful facts about how lenders look at their situation; exactly one question; no link and no push to DM; say "I work with Find Me Money Group."; never promise anything about their deal. Output: url | draft. DRAFT ONLY. Do not post.
{rows}
```

## REPORT · What did your scheduled sweep find today?

```text
READ ONLY. List every lead your scheduled tasks found since {date time ET}, in the LEAD ROW format, and say which task found each one. Then one line: the weekly allowance left.
{LEAD ROW format}
```

## SCHEDULE · Add a recurring sweep inside Muse (draft; needs Justin's yes before sending)

Creating a scheduled task changes Muse's config and spends its weekly allowance on every run, so it hasn't been tested yet. When Justin says yes, send this in the sweep side chat, then check it in Activity → "See all scheduled tasks" and with `cron.list`:

```text
Create ONE recurring task, daily at {5:00 PM} my time, titled "Afternoon funding sweep (agent)". Its prompt: "{FB-1 prompt text, including the READ-ONLY HEADER and LEAD ROW format}". Deliver the result to THIS side chat, not Main chat, wrapped in BEGIN-PM<YYYYMMDD> and END-PM<YYYYMMDD>. Do not change or delete any other task. Reply with the task id and next run time.
```

To remove it later (also needs Justin's yes): "Delete the scheduled task titled 'Afternoon funding sweep (agent)' only, and confirm with cron.list."
