---
name: wholesale-funding
description: Find Me Money's wholesale real-estate desk - find wholesalers who need cash (earnest money, transactional, gap, rehab or bridge funding), offer them funding through our partners, and pass their deals to partner buyers and lenders for a percentage, using the wholesaling method in Justin's private notes. We never put a house under contract ourselves. Use for wholesaler leads, a wholesale deal to place, a JV or finder-fee question, or the wholesale call cards.
---

# Wholesale: fund wholesalers, pass their deals

Justin, 2026-11-12: "We're also going to go after wholesale deals using the information we have from a wholesale course, wholesaling houses, because wholesalers need the cash, and offering the deals and working with them makes sense." His pick the same day: **fund them and pass deals; we never put a house under contract.**

The method is licensed course material, so it never ships in the pack. Justin gives it at intake; it lives at `/workspace/find-me-money/.secrets/course/method.md` (mode 600). Read it before the first run. **If that file is missing, stop the wholesale run and report blocked: `method notes not given (intake)`.** The steps below work without its details; the file adds the call script and the verify checklist.

## Two offers to a wholesaler

| Offer | What they need | Who fills it | Our pay |
|---|---|---|---|
| **Funding** | Earnest money (EMD), transactional (double-close) funding, gap or rehab money, a DSCR or bridge loan for a deal they keep | A funding partner (Lending Hub partners, hard-money and transactional lenders) | The partner's referral fee or our share, per `context/08-partners-and-commissions.md` |
| **Deal passing (JV)** | A buyer for a deal under contract that isn't moving | Partner buyers and lenders in our network | A JV fee or finder fee, protected in writing (below) |

## Where wholesalers come from (reads only)

1. The live `radar-cl` output: rows with `kind: wholesaler` and the "cash buyers", "assignment", "we buy houses" signals. Read them; never re-scrape those lists.
2. Radar asks in the real-estate categories (rea, rts, rew) and the Facebook and Skool wholesaling groups.
3. Muse's daily file (Facebook groups and Marketplace).
4. InvestorLift and similar inventory sites: **a sign-in Justin does** (on NEEDS-JUSTIN). Until then, public listings only.

## The daily run (wholesale role)

1. Pull today's wholesaler rows (1-3 above), newest first, nothing over 7 days.
2. **Find the right who** (the method's first step): for each, a call card in `requests/wholesale/card-<id>.md` with the deal, the verify questions (contract holder or a chain? days left in due diligence? access? the seller's reason? the bottom number for a fast buyer?) and the red flags (daisy chain, no access, no seller story, no flexibility).
3. **Match:** funding need → the partner desk's in-house-or-one-partner pick (`requests/partners/`). Deal to pass → the buyer and lender partners whose buy box fits (zip, type, price, condition, close speed), as a ranked list.
4. **Draft** the first touch to the wholesaler (type `fmm_wholesaler_first_touch`) and, only after a wholesaler said yes to sharing, the deal summary to partners (`fmm_deal_pass`). Both go through `send_guard.py`; until `auto` they sit in `requests/justin/`.
5. Log each in `vault/People/` by company only (no phones or emails in the vault) and end with `beat.py write wholesale 'wholesale' found=N cards=N matched=N drafted=N`.

## Gates of its own

- **Never** sign, send or fill a contract, a JV agreement, an assignment or payment instructions. Fee protection (a signed JV agreement plus title-company confirmation first; a settlement statement or invoice only where Justin says) is Justin's.
- **Never** promise a rate, an approval or a closing date for a partner.
- **No paid seller leads (paid lead engines are spend):** any paid list, lead provider or ad goes to `requests/justin/` as a plan with its cost.
- Home-secured or owner-occupied asks are commission only and held for Justin's routing (the funding charter's rule).
- Any activity targets in the method notes are a person's call targets, not send quotas for the bot.
