# Contact evidence and outcome rules

The alpha-v0.6.1 model keeps candidate identities and channels separate. Its primary candidate ranking is `8×role_supported + 4×identity_supported + 2×channel_supported + has_name + has_channel`. This chooses an evidence-rich record; it is not a probability of booking.

Identity support requires a checked source URL and text naming the person. Relevant conference roles include program/conference/scientific/track chairs, conference producers, event/content directors, speaker managers, speaker relations and published speaking-enquiry handlers. The source checks nearby text (approximately 140 characters each side) for role context. The agent should read the full visible card or section: proximity alone does not prove the role belongs to that person.

An unrelated faculty biography saying “Program Director” is not evidence of event booking authority. Confirm the role refers to the event, agenda, speaker selection or committee. An association's general leadership title likewise needs a demonstrated event relationship. Speaker-enquiry handlers are valid routes without being described as final selection decision-makers.

Email and personal LinkedIn ownership require the same person's card/text or an independently matched provider result. Do not attach a footer inbox to a nearby person's name. Keep conflicting nonempty channels as alternatives until resolved. Equal names are not enough to merge people if company, geography or role conflicts. Historical roles and related events remain leads until independently tied to this edition.

Record channel publication separately from email deliverability: `published_unverified`, `provider_verified`, `invalid`, `unknown`. DNS/MX existence proves a mail domain can receive mail, not that the person's mailbox exists. A page-level AI contact-verification badge is not a mailbox verification result. Provider verification should record provider, time and native result.

Source pipeline outcomes and agent meaning:

| Source value | Meaning |
|---|---|
| `complete` | Named role/channel evidence supports an actionable person; not a booking. |
| `complete_with_generic_contact` | Organizational route available; not a named contact. |
| `person_found_channel_missing` | Current or candidate person found, usable personal route missing. |
| `manual_review_required` | Evidence conflict, unsupported attribution or flagged contact. |
| `stale_or_closed` | Event passed or CFP closed; preserve for historical/future research. |
| `no_public_contact_found` | No supported route found so far. |

A case can have useful contact evidence while being ineligible for paid-only work. Keep opportunity eligibility and contact outcome separate. Likewise, do not lose an explicit organizer form just because named-contact research is exhausted.
