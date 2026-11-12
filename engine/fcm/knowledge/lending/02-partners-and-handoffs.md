# Partners and handoffs

From spec 36.

## 3. Partners: our CRM or theirs

Both, split by what each system is good at.

- **The lead and the conversation stay in our GHL.** Each partner gets a seat limited to their own assigned leads
  (`assignedDataOnly`). This is what makes "are they working it?" answerable: we can see the calls and messages.
- **The credit pull and application happen in the partner's own Funding Machine.** That keeps their process whole, and
  we never touch a credit report. They report the result back by moving the stage in our GHL.
- **A partner who won't take a seat** gets a private status link, one per lead, with no login: Contacted, Application
  in, Funded, Can't help. We then rely on what they tell us, so seats come first.

## 4. Pairing

Spec 35's gate stands: a lead can be handed off with **a real email, a phone number, and their OK** for a partner to
reach them. A website lead's OK comes from privacy policy section VI. Everyone else's is a stored quote in their own
words. Text consent never travels.

Added here:
- **Readiness.** `ready` goes to a closer. `prep` goes to a partner who takes credit or prep work, or to nurture if none
  fits. A lead no one fits is listed as unrouted, never forced.
- **Partner fit.** Each partner's entry holds lanes, products, states and `takes` (`ready`, `prep`), plus `situations`
  in plain words ("no startups", "needs 680+", "over $250k only"), so the agent can explain a pick.
- **No repeats.** Routing skips any partner who already had this person. A lead goes through at most three partners,
  then to Justin.

## 4a. Sold or commission

Justin, 2026-11-07: half sold, half on commission. The hub picks the route and gives the reason. Home-secured products are commission only. A credit repair referral is never sold. A sold lead still needs the person's own OK, and an
order never moves a lead who hasn't given it. Don't explain routes or prices to a lead.

## 5. The 7-day clock

Every number is in `config/handoff.json`, so Justin can change them without code.

| When | What happens | Who sees it |
|---|---|---|
| Sent | Intro goes to both sides. The lead gets the partner's name and number, the partner gets the context card | Lead, partner |
| 48 hours, no contact logged | Task and nudge to the partner | Partner |
| Day 3 | One light check-in with the lead: "Did they reach you?" | Lead |
| 72 hours, still no contact | Flagged for Justin as a likely re-pair | Justin |
| Day 7, no application or decision | The partner is asked where it stands, and Justin is flagged | Justin, partner |
| Day 7 | Second and last check-in with the lead | Lead |
| Day 9, still nothing real | Re-pair to the next partner who fits. Justin approves the new one | Justin |
| "Can't help", declined, returned | Re-pair at once to the next partner who fits | Lead, new partner |
| Funded | Justin marks it; expected pay is recorded | Justin |

**Not talking to two people at once.** While a partner has the lead, the CRM agent sends only the two scheduled
check-ins, and the Reply Agent drafts nothing. The partner owns the conversation. This is the same behaviour as the
affiliate agent's takeover tag, with one change: takeover sends nothing at all, and here two check-ins are allowed. If a
lead answers a check-in, the CRM agent records it and hands the answer to the partner.
