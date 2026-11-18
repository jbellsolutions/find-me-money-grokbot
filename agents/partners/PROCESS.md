# Partners, collaborators and influencers: the process

This function sends cold email, at volume, to people who could promote the business. A couple of them promoting in a month is the win.

The owner, 2026-11-16: "your job is to send 1,000 cold emails per day to potential partners, people who could be good promotional partners for the offer." "It sends a volume through Scale: 1,000 per day, 10 per inbox."

Everything on this page that is a rule is in his words. The rest describes how the work is done and can change without asking. Rules he did not state were removed on 2026-11-17; the few left in for his call are listed at the top of [STATUS.md](STATUS.md).

## Who is in this tier

The owner: "People who are Dream 100 and Dream 500 are already known to us as our perfect partners, and they're just the top-tier ones as far as followers, audience, and opportunity." "There's not going to really be a 10,000-follower floor, as much as there's somebody who's active, who's a good potential partner, but they haven't been identified as Dream 100 and Dream 500. It kind of is that simple."

So three questions, not a score:

| Question | Yes means |
|---|---|
| **Not on a dream list?** | They have not been identified as Dream 100 or Dream 500 |
| **Active?** | They are still at it: posting, publishing, running the group, trading |
| **A good potential partner?** | They have people who listen to them and could promote the offer to them |

There is no follower floor. An offline business counts: "It could be a consultant or coach of some sort. It could be a trades company."

"All types are in." The types in the settings example pick which email a person gets; they do not rank anyone, and a type that is not in the settings still gets emailed. Shows and podcasts stay with SpeakerAgent: a show host found here is handed over.

## What counts as a promotion

The owner: "A promotion could be anything."

- an email to their list
- a post
- a video
- a guest link
- an affiliate link
- a talk in front of their group

## What the email says

The owner: "We don't necessarily mention an offer unless there's an obvious pathway there. Partner gets something custom, so don't worry about it because we don't mention it in the email."

- The email does not mention the offer, unless there is an obvious pathway for that kind of partner.
- The email does not mention what the partner gets. That is custom, and it comes up after they reply.
- `prompts/first-email.md` is the brief the bot drafts each type's emails from.

## The number

| | |
|---|---|
| Emails a day | 1,000 |
| Each inbox | 10 a day |
| Inboxes that needs | 100 |
| New names a day | About 334 if each person gets a first email and two follow-ups |

`partners.py plan --settings <file>` prints these from a business's own settings.

Counting follow-ups inside the 1,000 is this chat's reading. If the owner means 1,000 new people a day, a three-email sequence needs 300 inboxes. The follow-ups and their days (4 and 10) are a default in the settings, not something he asked for.

## The steps

| # | Step | Who |
|---|---|---|
| 1 | **Settings.** The campaign's copy of `partners.example.json`: the offer and the buyer in plain words, the types, where the dream lists live, the sender, the number | The bot, with the owner |
| 2 | **Emails.** A first email and follow-ups per type, drafted from `prompts/first-email.md` | The bot |
| 3 | **Find.** Names per type from public sources. Fields: name, email, type, link, audience, last active, source, why. No paid enrichment service (the owner's standing rule) | The data lane |
| 4 | **Screen.** `partners.py screen` takes out anyone on a dream list, repeats and rows with no address, and sets show hosts aside for SpeakerAgent | `partners.py` |
| 5 | **Fit.** Each row gets yes, no or unsure with one line of reason from `prompts/partner-fit.md` | The bot |
| 6 | **Verify.** Addresses are checked before they are loaded | The cold email function's verification |
| 7 | **Load and send.** The day's rows go into that type's sequence in the sending tool, 10 an inbox | The sending tool |
| 8 | **Log.** Each send is written to the conversation log (the owner: "document all the conversations") | The send read |
| 9 | **Replies.** Every reply goes to the sales agent's inbox for this function. An interested partner goes to the owner with the thread, since what they get is custom | Sales agent |
| 10 | **Promotions.** One row per partner who said yes: what they will do, when, and the link once it is live | The bot |
| 11 | **Report.** Found, screened out by reason, fit, loaded, sent, replies, interested, promotions, by type | The bot |

Sending to people and new spend need the owner's yes. That is his standing rule for everything, not a rule of this function, and how he gives it for 1,000 a day is his to say.

## What it uses from other functions

The data lane builds the lists. Verification, inboxes, warm-up and the sending tool are the cold email function's. Replies go to the sales agent. Email is the first channel ("I'll just start with this"); nothing here reaches out on socials yet.

## Not built yet

- The find step as code. No source has been measured for how many usable partner addresses it gives a day.
- The load into the sending tool. The owner named "Scale", which is not a tool the kit has a path for (see `STATUS.md`).
- The promotions sheet's writer, and any link or code a partner promotes with.
- A check for `partners.py` in the template's self-test. It was tested by hand on made-up rows.
