---
name: radar-to-deal
description: The Lead Radar workflow, from a public funding ask to a Lending Hub deal. Read today's Funding Radar leads, judge each one the way the radar does (a US business owner's own debt-funding need, quoted word for word), draft the reply, and once the person engages, turn the conversation into a deal with the intake officer's flow. Use for "work today's leads", "who should we reply to", "turn this lead into a deal".
---

# Radar → deal

**Who owns what (doc 21).** Revenue Partner owns everything before a deal exists: finding, replying,
following up, and reading answers. The intake officer owns the deal from `received` on. Until Revenue
Partner's reply desk is built, the intake officer drafts the replies below. Once it runs, skip steps 1–3 and
start at step 4, when Revenue Partner hands over a person who engaged.

The Funding Radar finds people asking for business funding in public (Facebook groups through Google,
Reddit, YouTube, TikTok, Instagram, LinkedIn, Skool, forums). Each lead carries the author, the platform, a
permalink, a **verbatim quote** of their need, a tier (high / medium) and the campaign that found it.

## The mindset (same as the radar's)

- **The quote is the lead.** If the post doesn't show the author's own need in their own words, it isn't one.
- Sellers aren't buyers: lenders, brokers, ISOs, funding coaches and course sellers advertising are
  competitors, not leads.
- The need decides the product: "need $50K for two trucks, 2 years in business" is equipment or a term loan;
  "0% cards to start my LLC" is a card stack (startup); "behind on three MCAs" is consolidation.
- Fresh beats perfect. A reply within hours matters more than polish.

## Steps

1. `hub_today()`: today's likely-fit leads, newest first. Skip leads already in a deal (`hub_deals`).
2. For each lead, write a **strategy-first public reply** (the charter's agent brief): one or two useful facts
   about how lenders look at their exact situation, then exactly one question back, 85 words or fewer. The brand
   line is optional: "I'm with Find Me Money Group." No link and no DM push in a first touch, no rate but "0%
   credit lines", and never a guarantee or a promise about their deal; approval talk and "same day in some
   cases" only as claims, when true.
3. Drafts go to a human (or the radar-agent's sender when Justin turns auto-replies on). You don't post.
4. When the person replies or books, run the **funding-intake-officer** flow: `hub_extract` on the thread,
   `hub_create_deal` with `source = radar:<campaign>` and the permalink in the notes.
5. In GHL (when the funding profile exists), tag `src:radar`, `radar:<campaign>`, `geo:<metro>`, plus `fi:in-hub`
   once the deal exists (see `pinnacle-crm`).

## Platform rules that cost accounts (Justin owns these switches; they're on by default)

- Facebook and Instagram ban automated DMs and inauthentic accounts. Public replies, by a person or an approved sender.
- Skool: one follow-up after a "no", then stop; about 5 helpful replies for each 1 that mentions what we do.
- Reddit: follow the subreddit's self-promotion rule; DM only if invited.
- A public post is not consent to call or text (TCPA). Calls and texts start only after they opt in on our form.
