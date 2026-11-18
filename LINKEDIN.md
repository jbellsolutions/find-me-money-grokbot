# LinkedIn: the safety path

LinkedIn's User Agreement bans bots that post, comment or message, and it acts on it: the bot's cloud computer set off unusual-activity checks in an earlier build. Losing the account would cost more than every LinkedIn lead the agents could bring, so the template treats the account as the thing to protect.

## Three paths, in this order

| Path | What goes there | Where it runs |
|---|---|---|
| **1. OutFlo** | Connection requests, message sequences, first-degree messages, replies inside a campaign | In OutFlo, on the connection it keeps for that profile |
| **2. The owner's own computer** | What OutFlo can't do: posts, comments, replies to comments, DMs outside a campaign, reading the feed and the inbox | The computer and browser the owner already uses for LinkedIn, at a person's pace, or by the owner's own tap on a ready draft |
| **Never** | Anything | The GrokBot computer, a worker box, or any other data-centre address. LinkedIn is not signed in there, and `lane.py` refuses while `LINKEDIN_HOST` is set |

`linkedin/lane.py route <action>` gives the path for each action.

## How work reaches each path

The bot never touches LinkedIn. It prepares the work and queues it:

1. The agent writes the audience list or the message, logs the draft in the conversation log, and gets the approval the message type needs.
2. `lane.py order <action> ...` writes one work order to `linkedin/orders/` if today's cap allows it.
3. **OutFlo orders** are a campaign's audience file and copy. Whether the bot can load them through an OutFlo API is not known yet; until it is, the owner or the local runner imports them in OutFlo's own screen.
4. **Local orders** are pulled by the owner's computer. The bot never reaches into that computer: the local side fetches the queue from a private desk repo (the pattern the incubator kit uses), does each order in the owner's signed-in browser, and writes the result back.
5. Results come back as conversation-log lines: `sent` with the URL, or `failed` with what was seen.

The local runner is not built. Until it is, every local order is a ready draft the owner posts by hand, which is also the safest setting.

## Daily caps

| Action | Cap a day | Path |
|---|---|---|
| Connection requests | 20 | OutFlo |
| Sequence and first-degree messages | 50 | OutFlo |
| Posts | 1 | Local |
| Comments | 10 | Local |
| Replies to comments | 20 | Local |
| DM replies | 30 | Local |
| Feed or inbox reads | 6 | Local |

The 50 is the kit's existing cap for first-degree messages. The rest are starting numbers chosen for this template, not LinkedIn's published limits; a campaign may lower any of them and cannot raise one.

## The stop rule

On the first warning, checkpoint, identity check, CAPTCHA or "unusual activity" notice, on either path: `lane.py stop "<what was seen>"`. Nothing more is queued that day, and a note goes to the owner's queue. Nothing tries to get past it. The owner says when to go on.

## Before the first order

- The owner confirms with OutFlo how each profile connects (third-party pages say a residential address per profile; that has not been checked with OutFlo) and reconnects the account there.
- One browser profile, one computer, one place. Not a second profile, not a VPN that moves the address around.
- The first post and the first of each message type wait for the owner, like every channel.

## If OutFlo can't be used

The fallback is path 2 alone, with drafts the owner sends. If volume matters more than that allows, the choice of another tool is the owner's, made on how it connects each profile; the lane's caps and stop rule stay the same whichever tool it is.
