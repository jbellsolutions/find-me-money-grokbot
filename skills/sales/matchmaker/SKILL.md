---
name: matchmaker
description: Match two sign-ups for a commission referral campaign and carry the pair from introduction to a paid campaign. Use for the Referral desk run, a connection request from the site, a yes-reply handed over by outreach, or when Justin asks who should be paired with whom or where a pair stands.
---

# Matchmaker

A referral campaign: two businesses that serve the same kind of customer each send one email to their own list recommending the other, and each pays the other commission on the sales that come from it. Nobody shares a list. Each sends their own email.

## Who fits whom

Read `rc.py signups` (skip `spam` and `paused`). A good pair has:

- **The same area.** Same city first, then the same metro.
- **The same kind of customer, different things for sale.** Read `customers` and `wants`. A roofer and a gutter company. A gym and a physiotherapist. A realtor and a mover. A wedding venue and a photographer. Two businesses in the same trade compete, so they are not a pair.
- **Lists of similar reach.** `list_size` in the same band or the next one. A list of 200 and a list of 20,000 is a lopsided swap; if it is the only pair available, say so in the introduction.
- **Commission answers that fit.** Both named a percentage or a flat fee, or one is "Not sure yet". Someone who chose "My profession cannot pay referral fees" can still swap campaigns with no fee, and the introduction says that plainly.
- **What they asked for.** If `wants` names a kind of partner, that outranks everything except area.

A connection request from the site is already a pair: the visitor chose the listed business. If the visitor has not signed up themselves, the introduction asks them to (`/join`), so there is a record on both sides.

## Record it

`rc.py match <signup a> <signup b> --notes "<why they fit, in one line>"` creates the match as `proposed`. `rc.py matches` shows every pair with both businesses and emails. Stages, moved with `rc.py match-set <id> --status <stage>`:

| Stage | Means | Proof |
|---|---|---|
| proposed | The bot thinks they fit | The match record |
| introduced | The introduction went out to both | The sent message |
| agreed | Both said yes and agreed terms | Their replies |
| sent | Both campaign emails went out | Each one's word, or a forwarded copy |
| paid | A commission was paid at least one way | Either one's word |
| dropped | One said no or went quiet | The reply, or two unanswered follow-ups |

## The introduction (message type `rc_introduction`)

One email to both people. It has:

1. Who each of them is, in one line each, from their own sign-up answers: name, business, what they do, where.
2. Why the two fit: the shared customer.
3. How it works, in three lines: each emails their own list about the other, once; they agree a commission first; nobody shares a list.
4. The three things to agree before either sends: what counts as a referred sale and how both will know; what is paid on it and when; the date each sends.
5. A sample campaign email they can rewrite, built from the other one's business (see the example on the site's home page for the shape). Mark it as a starting draft.
6. What to do next: reply-all to say hello.

Run `suppression.py check` on both, then `send_guard.py rc_introduction`. Not `auto` means the draft goes to `requests/justin/`. After it is sent: `rc.py match-set <id> --status introduced`, and `rc.py signup-set <id> --status matched` for both.

## Following a pair (message type `rc_match_followup`)

On the follow run read `rc.py matches`. For each `introduced` or `agreed` pair with no movement, draft one short note asking where they got to and offering the next step (the three things to agree, or a send date). A reply about price, a dispute between the two, or a contract goes to `requests/justin/`. When a pair reaches `paid`, ask both whether they would like another partner in a different category, and write one line for the scoreboard: the area, the two categories, the stage. No names.
