# Lead Radar: the process

Lead Radar brings the leads and opportunities in the door. It reads social media and communities for people already talking about what the business sells, judges each post, hands the real ones to the sales agent who starts the conversation, lists the influencers and partners it comes across, and holds the data for the email campaigns.

The owner, 2026-11-17: "this is really our star of the show. It's what nobody else does." And: "This is very much the star of the show, the quarterback."

Everything on this page is either the owner's own words (quoted, with the date) or a description of how the build works. A description is not a rule: change it when it is in the way. The few safeguards a chat added and left in are on the keep-or-remove list at the top of `STATUS.md`.

## The four routes

The owner, 2026-11-17 (dictated; "Trig" is read as Treg, "WOP and WHOP" as Whop, "Consulti.ai" as Consulti):

"For partnerships right now, let's do SKOOL.com and WOP and WHOP. For leads, SKOOL.com and WOP. We're going to be joining groups, scraping comments and posts, looking for potential lead opportunities. For data, we're going to use Trig as well as Consulti.ai. For social media, we'll scrape Facebook, Instagram, and Reddit to start with."

| Route | Where, to start | What comes out | Goes to |
|---|---|---|---|
| **Social media** | Facebook, Instagram, Reddit | Posts and comments where someone is talking about the offer, judged 1 to 5 | Kept leads to the sales agent |
| **Community leads** | Skool and Whop groups | The groups' posts and comments, judged the same way | Kept leads to the sales agent |
| **Partnerships** | Skool and Whop | A list of possible influencers and partners, group owners first | The partners function |
| **Data** | Treg and Consulti | The lists the email campaigns send to | The email campaigns |

The other social channels (LinkedIn, TikTok, YouTube, X) are in the settings, switched off to start.

## The tools

- The owner, 2026-11-17: "starting first with our scraping capabilities and then also using Trig. With Trig come scrape creators and all the other different tool opportunities that come with it." And: "We might even use other tools, like, for instance, the MetaMuse tool."
- The owner, 2026-11-16, on which radar this is: "both but we want to build the agent with treg, and One api as the main one here for the grokbot". A dashboard radar a business already runs is one more source.
- The owner, 2026-11-16: "the One API actually has Treg in it. I think Treg for clients is going to be the appropriate way, because I don't think I can give them access to One API while also not shouldering some of the cost." And: "it starts off with all the free sources of scraping and writing your own scrapers, etc., and then moves into using Treg for scrape creators and things like that."
- The owner, asked 2026-11-16 whether the standalone Lead Radar agent is kept out of a Revenue OS business: "No, it stays". Asked whether it hands its leads over: "Yes, hand them over".
- Data tools. The owner, 2026-11-07 (recorded in the kit's Consulti skill): Consulti and Treg are all the data needed for now. His standing instruction of 2026-05-25: no paid enrichment services.

So `account` in the settings picks the set-up:

| | The owner's own businesses (`account: owner`) | A client's business (`account: client`) |
|---|---|---|
| Call path | One API, the owner's gateway, with Treg inside it | The client's own Treg team |
| Who pays | The owner | The client |
| Order tried | Free reads, then the owner's own scrapers, then Treg | Free tools in Treg's catalog, then its paid ones |

Sources a campaign can switch on beside these: a dashboard radar, the standalone Lead Radar agent, MetaMuse, the Grok bot's own X search.

Two facts about the tools today:

- One API carries eleven fixed Treg social reads plus web search and extract. Keyword search on Reddit, TikTok, X, Threads and YouTube is in Treg and not yet in One API.
- Treg's catalog has no read for Skool or for Whop (searched 2026-11-17). Those two, and private Facebook groups, are read through a signed-in browser.

## What Treg carries that is not used yet

Read from Treg's catalog on 2026-11-16 (searches only, nothing called). Prices are the catalog's and change.

| Job | In the catalog | Used today |
|---|---|---|
| Keyword search on Reddit, TikTok, X, Threads, YouTube, LinkedIn posts; Instagram by hashtag | Yes, several providers each, most with a routed `treg.<job>` id; a fraction of a cent per call | Reddit and group reads only, through ScrapeCreators |
| Comments on a YouTube video; YouTube search; recent Instagram posts for a hashtag | Yes, with **free** tools | No |
| Facebook group posts by group | Yes, two providers | Yes, in one application |
| Creators by niche and size; profile search | Yes | No (the partners function pulls creators another way) |
| Local businesses from Google Maps | Yes, routed | No |
| Job postings (a business hiring for the work is a buyer) | Yes, routed | Only in the dashboard radar |
| Ad libraries (who is advertising in the category) | Yes, with a free Meta tool | No |
| Company news and funding | Yes, with a free feed | No |
| People at a company by title; work email find; email verify | Yes, many providers, some free | The data route, not built yet |

## Who does what with a kept lead

The owner, 2026-11-16: "need to start a convo - thats CRM sales agent. reply agent makes sure all replies are taken care of and leads are moved to the next stage. crm sales agent does the work to move them through the pipeline and cover as well". Asked whether a kept lead goes to the reply side and the CRM at once: "Yes, both at once". On 2026-11-17 he made the reply agent and the sales agent one agent ("Yes, one agent"); in the template that agent is `sales-crm`.

The owner, 2026-11-17: "those are getting passed off to the CRM agent, who's a sales agent. That agent is then starting conversations and replying to those conversations, documenting, adding to CRM, and doing its job."

So Lead Radar finds, judges and hands on. The sales agent starts the conversation, replies, documents and writes the CRM.

## Skool, Whop and Facebook groups

The owner, 2026-11-16: "Facebook and Skool as well, correct? Skool is also for the influencers as well, though." And: "We'll message all the group owners as influencers to do collaborations, and then we'll also scrape all the Skool groups, the posts, and the comments for potential leads." And: "the main thing is leads for sure". On 2026-11-17 he added Whop, and: "making a list of potential influencers and partners".

- In each group, Lead Radar reads the posts and the comments and judges them like any other post.
- It keeps the list of possible influencers and partners (`state/lead-radar/partners.jsonl`) and puts a pointer for each new name in `requests/partners/`.
- These groups are read through a signed-in browser, since no scraper or Treg tool reads them.

## The data route

The owner, 2026-11-17: "This agent's also the one that is in control of the data for the different email campaigns." And: "For data, we're going to use Trig as well as Consulti.ai."

Nothing is built for this route yet.

## The steps

| # | Step | Who |
|---|---|---|
| 1 | **Settings.** The campaign's copy of `lead-radar.example.json`: the offer and the buyer in plain words, leave-outs, channels, terms, groups, the keep line | The bot, with the owner |
| 2 | **Search plan.** Per channel: the phrases people use when they ask ("need a", "looking for someone to"), and the places to watch (groups, boards, posts whose comments are read) | The bot |
| 3 | **Read.** Each channel's posts and comments, through the sources above | The bot |
| 4 | **One shape.** Every post becomes `{id, channel, url, author, text, posted_at, source}` in one `found.json`, whatever brought it | The bot |
| 5 | **Judge.** `radar.py score --items found.json --settings <file>` drops channels that are off and posts already seen, then sends the rest to Codex through `engines/route.py --agent lead-radar` with `prompts/lead-fit.md` | Codex, then Claude Code, then the bot |
| 6 | **Keep.** Score 1 to 5; `keep_at` and up are kept (4 in the example). A post no engine judged is kept and marked "not judged" | `radar.py` |
| 7 | **Suppression.** Each kept person is checked against the business's suppression list (on the keep-or-remove list) | `radar.py` |
| 8 | **Log.** Each kept post is one inbound line in the conversation log. The owner, 2026-11-16: "It's vitally important that we do document all the conversations that we're having" | `radar.py` |
| 9 | **Hand on.** One file per kept lead in `requests/sales-crm/radar-<date>-<n>.md`: the link, their words, the score, the need, an angle | `radar.py` |
| 10 | **CRM.** The sales agent records the line from the conversation log | The sales agent |
| 11 | **Report.** Found, new, kept, not judged and suppressed, by channel, in the run log (`log/lead-radar-<YYYY-MM>.jsonl`) | The bot |
| 12 | **Tune.** Which phrases and places brought kept leads and conversations | The bot |

Steps 5 to 9 are one command, built and tested with stand-ins. Engine: the owner, 2026-11-16: "Our Lead Radar can use our Codex CLI".

## Settings a campaign can use

All optional, none a rule: `keep_at` (the score kept from), `max_age_days` (drop posts older than this; no age limit when left out), `leave_outs` (kinds of post scored 1), spend caps (`max_usd_per_call`, `daily_cap_usd`), which channels and sources are on, and `hand_off.first_message` (the folder kept leads go to).

## Not built yet

- The reads themselves (steps 2 to 4) as code: today the bot does them with its One API and Treg skills.
- The signed-in read for Skool, Whop and private Facebook groups (the kit's `skool-inbound` skill is the starting point; nothing exists for Whop), and the partner list.
- The data route.
- Sources into `found.json` from a dashboard radar (the kit's `radar_poll.py` does this for the kit's worker), from the standalone Lead Radar agent and from MetaMuse.
- A first-message type for the sales agent on every channel Lead Radar finds on.
- A check in the template's self-test for `radar.py`. It was tested by hand against a stand-in Codex and a stand-in suppression guard.
