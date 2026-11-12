# Partners and commissions

How the partner lane works. Partner names, terms and rates are Justin's and set at intake; none ship here.

## How it works

- **Pairing:** a hard filter (products, states, amounts), then a score (product fit, funded rate, open orders, current load), then a route with a one-line reason.
- **Two pay types:** a lead is either sold per lead or sent on commission, never both, with a reason on every route.
- **Handoff states:** proposed, approved (a person only), sent, accepted, funded, paid; or declined, returned, cancelled. The payload is frozen at proposal.
- **Ledger:** a lead fee on send (from a prepaid balance first), a commission on funded. "Paid" comes only from a verified payment event or a signed-in person.
- **Lead orders and private links:** a partner orders by product, state, volume and price through a signed link.

## The rules in force

| Rule | Enforced by |
|---|---|
| A lead moves only with the lead's own OK, quoted in their words | `fcm_partner_ok`, the hub |
| Consent to text never travels to a partner | the hub |
| Home-secured loans are commission only, never sold per lead | routing config |
| One open handoff per contact; a few partners at most over time | the hub's distribution config |
| Activating a partner, or sharing a lead, needs Justin's yes | send_guard, GATES.md |
| Only Justin or a verified payment marks Funded or Paid | the hub |
| Partner names never appear in public copy | the charter skill |

## What the partners role does until Justin names a partner

Proposes in-house or one candidate partner per applicant with a reason, in `requests/partners/`, and nothing else. No partner is active until Justin names one with products, states and pay (NEEDS-JUSTIN).
