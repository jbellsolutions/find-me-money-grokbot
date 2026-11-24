# Job: partnerships

Affiliates and referral partners: the lists, the first messages and the partnership emails. Justin, 2026-11-24: "we need to really focus in on building affiliates and referrals, maintaining a pipeline for them, and really hit those channels pretty hard."

The number: `affiliates_and_referrals` in `context/targets.md` (70 a day to start, shared with the communities job): that many new people found, each with a first message drafted. An **affiliate** promotes Find Me Money to an audience. A **referral partner** serves owners one at a time and sends the ones who need funding.

On cold email, the same day: "It'll still do some cold email through partnerships, for partnerships, but not for direct leads, at least not for right now."

A partner is someone who already has business owners gathered around them: funding and credit creators, business coaches, community and group owners, accountants and bookkeepers, wholesaler communities, local associations. **A business owner who might need funding is a lead, not a partner, and never gets a cold email from this bot.** A lead found here goes to `requests/sales/leads-<today>.md` and nowhere else.

## Read first

- `context/revenue-os/find-me-money/dream-100.json`, `dream-500.json`, `partners.json`, `cold-email.json`.
- `repo/agents/dream-100/PROCESS.md`, `repo/agents/dream-500/PROCESS.md`, `repo/agents/partners/PROCESS.md`.
- `requests/partnerships/`: what Lead Radar and the communities job found. `data/partners/community.csv`.
- `data/dream100.csv` if it is there.

## Do

1. **Find.** Add new candidates from public sources (WebSearch, WebFetch) until the day's number is met (what the communities job added today counts), each with the public page that shows their audience. No paid data source.
2. **Screen and place.** `python3 repo/agents/partners/partners.py screen --rows <found.csv> --settings context/revenue-os/find-me-money/partners.json --out data/partners/<today>/`; then `python3 repo/agents/dream-500/dream500.py place <kept.csv> --settings context/revenue-os/find-me-money/dream-500.json --out data/partners/<today>/`. The biggest audiences go to the Dream 100 file; score each with `python3 repo/agents/dream-100/dream100.py score`.
3. **Dream 100: one to one.** For the next five without a first touch: a short dossier (`data/partners/dossiers/<name>.md`: what they make, who follows them, one thing they said lately) and a first message that could only have been written to them. Message type `partner_message`.
4. **The wider list: the partnership email.** For the next wave (the number in `dream-500.json`): a first line for each from their own public work, on the sequence in `content/partner-sequence.md`. If that file is not there, write it first: three emails, the first under 90 words, offering the partnership in plain terms (what their people get, what they get, what it costs them: nothing). Message type `partner_cold_email`.
5. **Follow-ups that are due**, from `data/partners/sent.csv`, drafted the same way.

Before any draft to a person: `python3 repo/guards/scripts/suppression.py check "<who>"`; `held` means skip. Each draft is an item file in `requests/justin/` (ITEM, ROLE, ---PAYLOAD---, TO, SUBJECT, TEXT, ---END---) logged with `CAMPAIGN=find-me-money python3 repo/convlog/gate.py drafted <file> --agent partners`. A wave is one item whose TO names the list file.

6. Hand every one touched to the sales job, which keeps their pipeline: `requests/sales/partners-<today>.md` (name, affiliate or referral partner, audience, source, the stage they are at).

Nothing is sent from this job. A send is the bot's, after Justin's yes to that message type and his word on the sending tool.

## Write

`daily/<today>/partnerships.md`: found against the number, kept, placed in each list; first touches and emails drafted; follow-ups due; anyone skipped by the opt-out list.
