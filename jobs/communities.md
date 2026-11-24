# Job: communities

The Skool and Whop groups, for partnership and outreach. Justin, 2026-11-24: "it's working our SKOOL groups and WAP groups for partnership and outreach."

## Read first

- `context/communities.md`: the groups. One line each: `<name> | skool or whop | <url> | signed-in or public | ours or theirs`. If it is not there, write it first from a public search: 15 Skool and Whop communities of business owners, real estate investors, credit and funding, and local business, each with its public URL and member count, all marked `public`. Put the list in `requests/justin/communities-to-join.md`, once, so Justin can say which to join.
- `data/communities/<today>/*.txt`: what the bot's browser saved from the signed-in groups today. For a `public` group, read its public page yourself with WebFetch.
- `context/revenue-os/find-me-money/partners.json` and `repo/agents/partners/prompts/partner-fit.md`.

## Do, for each group

1. **Affiliates and referral partners.** The owner, the admins and the members who plainly have their own audience of owners, or who serve owners and could refer them (bookkeepers, accountants, coaches, agencies, equipment and real estate people). Add each to `data/partners/community.csv` (name or handle, group, role, what their audience is, the public source, why they fit). No private contact detail that was not posted in public.
2. **Asks.** A member asking for funding goes to `requests/sales/leads-<today>.md`, like a Lead Radar find, with the group as the source.
3. **What the group talks about.** The questions asked most, without the people, into `content/ideas.md`.
4. **Drafts**, each an item file in `requests/justin/` logged with `CAMPAIGN=find-me-money python3 repo/convlog/gate.py drafted <file> --agent partners`:
   - For a group that is `theirs`: one message to the owner proposing a partnership (a funding lesson for their members, or a seat as their funding resource), and one to each member worth having as an affiliate or referral partner, specific to what their group is about. Message type `partner_message`. Check `python3 repo/guards/scripts/suppression.py check "<who>"` first.
   - For any group where it would help: one post or comment that teaches one thing and sells nothing. Message type `community_post`. A group's own rules, where posted, are followed; a group that bans promotion gets a teaching post with no mention of the site.

The bot never posts, comments, messages or joins. Every one of these is a draft until Justin has approved its type.

## Write

Everything added here counts toward `affiliates_and_referrals` in `context/targets.md`.

`daily/<today>/communities.md`: groups read (signed-in and public), groups that had no saved text, partners added, asks handed over, drafts made.
