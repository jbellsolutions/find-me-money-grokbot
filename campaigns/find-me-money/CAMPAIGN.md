# Find Me Money (findmemoneyapp.com)

Justin, 2026-11-24: "100 leads, 100 conversations started a day... we need to really focus in on building affiliates and referrals, maintaining a pipeline for them, and really hit those channels pretty hard. We have our direct leads with Lead Radar, and then the rest of it's just affiliates and referrals, and then we have our AEO SEO."

The message: [MESSAGING.md](MESSAGING.md). The plan: [LAUNCH.md](LAUNCH.md). The two numbers: `context/targets.md`.

## Who it is for

- **Direct leads:** people and business owners looking for funding, found by Lead Radar and by search.
- **Affiliates:** people with an audience of owners who would promote Find Me Money to it: funding and credit creators, business coaches, community and group owners.
- **Referral partners:** people who serve owners one at a time and can send the ones who need funding: bookkeepers, accountants, agencies, equipment sellers, real estate people.

## What the bot does

| Job | Here |
|---|---|
| Lead Radar | Direct leads: public asks for funding, a helpful draft answer for each |
| Partnerships | The affiliate and referral partner lists; one-to-one first messages; the partnership email sequence |
| Communities | The Skool and Whop groups: affiliates and referral partners there, asks, what the group talks about |
| Sales | Every reply answered; GoHighLevel: a pipeline for direct leads and one for affiliates and referral partners, every person with a stage and a dated next step |
| Content | Six pieces a day on the eight pillars and the eight money hooks. Words by the Claude Code CLI, talking videos by HeyGen |
| AEO and SEO | The front page of Google and AI answers: the weekly read, one page and one video brief a week |

## The numbers, and where each comes from

| Number | Source |
|---|---|
| Leads a day, of 100: direct, and affiliates and referral partners | `requests/sales/`; `data/partners/` |
| Conversations started a day, of 100; first messages ready and not sent | The conversation log |
| Affiliates and referral partners by stage; leads each has sent | The CRM's partner pipeline |
| Replies in and answered | The conversation log |
| Pieces drafted, rendered and posted | `content/drafts/`, `log/heygen.jsonl`, each outlet |
| Named on N of 15 questions; leads from search | `data/aeo/` |
| Jobs carried by Claude Code, Codex and the bot | `python3 repo/tools/job.py audit` |

## Not this bot's

- Cold email to a direct lead. Cold email is for affiliates and referral partners only.
- The Referral Connection site and SpeakerAgent.
- A reply-to-every-pitch text campaign runs on Justin's own computer. The bot does not send it.
