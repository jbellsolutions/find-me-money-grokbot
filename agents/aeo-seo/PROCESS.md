# AEO and SEO: the process

The goal is inbound leads from search engines and AI engines, as many as the business can take. Being named, cited or ranked is how that happens, not the result. RankSpot is one tool in it: the checker and the reader. Version 0.2.

The owner, 2026-11-17: "the goal here is generating as many inbound leads as possible from search engines and AI engines. Your Google answers are your best spots. Rank it on the front page of Google, especially using video, but stuff that's going to convert, not just any video. Then get it seeded in ChatGPT and Google, get those going, and make sure that we're ranking. RankSpot's a great tool. It's not our only function."

## The four jobs, in the owner's order

| # | Job | What it means here | Measured by |
|---|---|---|---|
| 1 | **Take the best spots on Google** | For each buying term: the AI answer at the top, the featured answer, the video results, then the ten links. One page per term that opens with the direct answer, and one video for the same question | Front-page terms out of the target list (Search Console position 10 or better), and clicks |
| 2 | **Video that converts** | Video is the first choice for a buying term. Not any video: the buyer's question as the title, the answer in the first 30 seconds, and one next step (the call). This function writes the brief and places the finished video; the content function makes it | Videos live per buying term; leads whose source is a video |
| 3 | **Seed the AI engines** | Get the same answer, with the business named the same way, into the places the engines read: the site's answer pages, the videos and their descriptions, Medium, directories, partner and podcast pages | The share of panel answers that name the business, per engine |
| 4 | **Make sure we are ranking** | The weekly read, below. What moved, what is still missed, and the fix for each, buying questions first | The read itself, every week |

Above all four: **inbound leads from search, AI engines and video**, counted by the CRM sales agent. A week where rank rose and leads did not is reported as that.

## What goes after what

- **Buying terms first.** Every target term and panel question carries an intent: buy, compare or learn. Pages, videos and fixes are listed buy first, then compare, then learn.
- **One question, one page, one video, one next step.** The page answers the term in its first lines and carries the video; both end on the call.
- **The target list** is `data/aeo/terms.json`: the term, its intent, the page, the video. The AI panel (`data/aeo/prompts.md`) is the same questions as a buyer asks an AI.

## The video brief

The owner asked for video that converts, "not just any video". This function's reading of that, as what a brief to content holds: the buyer's question as the title in their words; the answer in the first 30 seconds; one next step, said in the video and first in the description. The three points are this function's draft, not the owner's words. When the video is live this function places it: embedded on the page that answers the same question with video schema, chapters and a full description, the transcript on the page, and the link in the citation queue. Publishing needs the owner's yes.

## Who does what

| Part | Who | Pays with |
|---|---|---|
| Asks each engine the panel's questions, every day, and saves the answers | RankSpot's own daily run | RankSpot prepaid credit: the only money in this function |
| Reads the saved answers, cited pages, the searches the engines ran, and the site's Search Console numbers | `aeo.py pull`: reads only | Free |
| Counts the leads whose source is search, an AI engine or a video, and writes `data/aeo/leads-<date>.json` | The CRM sales agent | Its own engine |
| Counts: the share of answers that named us, per engine, against the period before | RankSpot's summary, written out by `aeo.py read` | Free |
| Judges each missed answer: who was named, what was cited, the one fix | Codex through `engines/route.py --agent aeo-seo`; Claude Code only as fallback | The ChatGPT subscription |
| Plans, asks for the owner's yes where his rules call for it, hands briefs to the other roles | The bot | The Grok plan |

Engines RankSpot's API reports on: ChatGPT, Perplexity, Google AI Overviews, Google AI Mode. Its site also names Claude and Gemini; the API's list does not. Grok is not covered.

## Setting it up for a business

| # | Step | Who | Needs the owner |
|---|---|---|---|
| 1 | Copy `aeo.example.json` into the campaign's settings. Fill the site, the business in the buyer's words, and the one way its name is said everywhere | The bot | No |
| 2 | Write the target list (`data/aeo/terms.json`) and the first panel (`data/aeo/prompts.md`): 12 questions to start, buying ones first, each with its intent and where it came from (a call, a reply, a Lead Radar ask, People Also Ask) | The bot, from the other agents' files | No |
| 3 | `aeo.py cost`: the month's cost of that panel at the listed price, against the cap in the settings | Script | No |
| 4 | The owner signs up or signs in to RankSpot, connects the site, tops up, makes an API key, and puts it on the computer by hidden prompt under the name in `rankspot.key_env` | The owner | His sign-in and his spend |
| 5 | The owner (or the bot on his typed yes, question by question) adds the panel in RankSpot and turns the daily run on. This is the switch that spends. RankSpot's other schedules (keywords, backlinks) spend too, so each is his yes | The owner | New spend |
| 6 | Verify the site in Google Search Console and Bing Webmaster; connect Search Console in RankSpot. Without it Google rank is not measured, and the read says so | The owner | His sign-ins |
| 7 | After the first full week of answers, run the read once. That read is the baseline: it is recorded, not compared | The bot | No |

## The weekly read

| # | Step | Command |
|---|---|---|
| 1 | Read the last 7 days: Search Console position and clicks per search and page, how the site showed up (video and other result types), the AI summary for this period and the one before, every answer, the full text of each answer that did not name us, the most-cited pages, the searches the engines ran, new People Also Ask questions | `aeo.py pull --settings <file>` |
| 2 | Judge each missed answer. Codex returns the question's intent, the kind of source the engine leaned on, one fix from the list the campaign switched on (or none), and a one-line brief | `aeo.py judge --settings <file>` |
| 3 | Write the read, in this order: inbound leads; Google (front-page terms out of the target list, buying terms first, with the page and the video for each); AI engines (the shares, who is named instead of us, the pages cited most, the searches we have no page for); the fixes grouped by owner, buying questions first | `aeo.py read --settings <file>` |
| 4 | Hand over. One file per owner role in `requests/<role>/aeo-fixes-<date>.md`. The bot picks the three that matter most and says so in the owner's report | The bot |
| 5 | Panel upkeep: propose questions to add (from new asks and the engines' own searches) and to drop (not ours to answer), with the new cost line. A change that raises the cost is new spend: the owner's yes | The bot |

If no engine answers in step 2 the answers are marked "not judged" and the bot reads them itself.

## Where a fix goes

| Fix | Owner | How it leaves |
|---|---|---|
| `answer_page`, `site_fix` | This function | A page that opens with a 40 to 60 word direct answer, a named source and a date, with an FAQ block and schema. As a pull request the owner merges, or as a package (the files and their checks) when someone else runs the site. A direct write to a live site is a production write: the owner's yes |
| `medium_piece` | This function | A draft in the owner's signed-in Medium; publishing is the owner's yes |
| `video`, `post` | Content | A brief in `requests/content/`; content drafts it |
| `guest_post`, `directory_listing` | Partners | A brief in `requests/partners/` |
| `podcast` | Speaker | A brief in `requests/speaker/` |
| `forum_answer` | Reply | Switched off in the example settings: the reply agent has no forum channel yet |

`data/aeo/citations.md` is the list of live links that mention the business, so the read can tell which ones an engine picked up.

## The line between this function and content

Proposed by this function's chat; the owner has not said it. This function does what gets the business cited and found: the panel, the reads, the citation queue, the site's structure, and pieces written to answer one panel question. Content does what is made to be shared. They meet at two hand-offs: a brief going to content when the fix is a video or a post, and a published link coming back for the queue.

## The owner's rules that apply here

There are no rules in this function except the ones the owner stated. These are his, with where he said them:

| Rule | His words | Date |
|---|---|---|
| Inbound leads are the goal | "the goal here is generating as many inbound leads as possible from search engines and AI engines" | 2026-11-17 |
| Google's front page, with video that converts | "Rank it on the front page of Google, especially using video, but stuff that's going to convert, not just any video" | 2026-11-17 |
| Seed the AI engines and check the rank | "get it seeded in ChatGPT and Google, get those going, and make sure that we're ranking" | 2026-11-17 |
| RankSpot is used, and is not the whole function | "RankSpot is great. We're definitely going to use it"; "It's not our only function" | 2026-11-17 |
| Sends, publishing, new spend, deletes and writes to a live site need his yes | His global instructions: "These still need an explicit yes every time" | standing |
| No paid enrichment. This function reads RankSpot's email finding (paid, per email found) as that, so it is not used; its pitch emails are sends | His global instructions: "No paid enrichment services in agent plans" | 2026-05-25 |
| No key in a settings file or a page | His global instructions: "Never echo a secret back or put one in a summary, a page, a repo" | standing |
| No partner name, contact list or private figure in what ships | His global instructions, the pack exception | 2026-11-12 |

The engine for this function (Codex, Claude Code as fallback) is the product's engine table, kept in the main chat's `RULES.md`.

Checks that are in the code and are not in his words are listed at the top of [STATUS.md](STATUS.md) for a keep or a remove. They are still in until he says.

## What this version leaves out, on purpose

- **Who writes the piece.** A fix is a brief. Whether Codex or Claude Code drafts an answer page or a Medium piece is the owner's call, not made here.
- **Articles through RankSpot** ($3 each). `articles_a_month` is 0 in the example. The kit's gate script for them names two sites in its code and needs settings of its own before another business can use it.
- **The audit of a prospect's AI visibility.** It is a sales offer; off until the owner prices it and says which function runs it.
- **The kit's full SEO campaign** (thirteen roles and a board). It stays the library the fixes are written from; whether it runs as a method is not decided.
- **How a lead gets its source.** The read shows leads only when the CRM sales agent writes the count. The conversation log has no source field for search, AI engine or video yet, and no landing page or booking form marks one: proposed to the main chat.
- **Which Google spot we hold.** Search Console gives position and whether a video result showed; it does not say whether the AI answer at the top named the business. RankSpot's Google AI Overviews and AI Mode answers cover that for panel questions only.
- **Making or uploading a video,** and the brief as a file with its own check. The brief's three points are settings; nothing checks them.
- **Engines RankSpot does not cover.**

## Tested, and not

Tested on a Mac on 2026-11-17: the self-test (every non-read path refused, a key for another site refused, the one POST is the search read, a switched-off fix dropped, buying terms listed first, STOP), the cost line, and one real judge call through the router on Codex with made-up answers, one carrying a planted instruction that was ignored. Not tested: any call to RankSpot (no key, no workspace), so the field names rest on its published API description, the Search Console read most of all; the judge prompt's new intent field against a live engine beyond one call; and anything on a Grok bot's computer.
