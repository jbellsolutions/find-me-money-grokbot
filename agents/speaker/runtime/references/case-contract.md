# Portable case and mission contract

Store private work under a client-specific workspace, not inside the distributable skill. Recommended layout: `persona.json`, `mission.json`, `cases/<case_id>.json`, `actions.jsonl`, `brief.md`, `sources/`. Give each mission one active writer. Profiles alone do not enforce concurrent file locking.

The JSON examples in [assets](../assets/persona.example.json) are portable shapes, not SpeakerAgent database payloads. Source API fields use a mix of Airtable display-case and snake_case; translate deliberately instead of uploading these files to an uninspected endpoint.

Required case fields:

| Field | Meaning |
|---|---|
| `schema_version`, `case_id`, `client_id`, `persona_id` | Explicit identity and schema. |
| `kind`, `name`, `official_url`, `edition` | Conference/podcast identity; edition for events. |
| `observed_at`, `sources` | ISO date/time and source list; each source has `id`, `url`, `observed_at`, short `excerpt` or `summary`, `checked`. |
| `fit` | Verdict matched/rejected/unreviewed, exact best_topic, reason, source_ids, optional score/version/components/confidence. |
| `event_date`, `cfp_deadline`, `cfp_status`, `event_format`, `location` | Separate date/CFP facts; null or unknown if unestablished. |
| `eligibility` | eligible/ineligible/unknown, reasons and source_ids. |
| `compensation` | status, amount_min, amount_max, currency, session_type, source_ids, speaker_context_checked. Never fill fee from tickets. |
| `contacts` | Candidate-specific name, role, channel, identity/role/channel flags, historical flag, source_ids, deliverability. |
| `route` | named_actionable/organizer_route/application/none/manual_review, URL or email, source_ids, verified purpose. |
| `qualification` | accepted/research_hold/rejected/watchlist; distinct from SaaS sales status. |
| `draft` | status absent/draft/reviewed/sent/submitted, version and file path; factual claims trace to sources/persona. |
| `research` | attempted strategies, visited URLs, actual costs, pending jobs, next action, stop reason. |
| `event_type` | Optional agent extension: conference, seminar, webinar, workshop, panel, summit or corporate_training. The shared event record keeps `kind: conference`. |
| `pipeline` | Optional local workflow: status, next_action_at, suppression, history. Status can be discovered, researching, qualified, drafted, approved, contacted, replied, booked, declined or closed. Each real external transition needs a timestamp and receipt/source; a draft does not mean contacted. |

Use [case template](../assets/case.example.json). Missing is not false or zero: use null/unknown. Keep confidence and evidence separate. Report source observation time, not just the date the summary was written.

Use `excerpt` only for a short exact quotation. Put a paraphrase or synthesis in `summary`; never present rewritten source text as a quotation. Resolve conflicting persona/mission payment policies before unattended operation. When the client changes their preference, update both records and preserve that decision in mission history.

Public sources use `kind: public` (the default), a real HTTP(S) `url`, observed_at and checked evidence. Client-supplied speaker facts use `kind: client_supplied`, a workspace-relative `path` such as `persona.json`, an `attribution` such as “client-provided persona”, observed_at, checked and summary. Do not put a filename into a public URL field or invent a web URL for private evidence. The runtime checks the local evidence file exists. Client evidence can substantiate the speaker's own background; accepted event fit/eligibility still needs official/public event evidence, and a persona assertion alone cannot establish event payment or a contact's channel ownership.

Event identity should include the normalized official URL plus event name and edition/date under the client/persona. Drop tracking fragments/UTM parameters, preserve meaningful path/query identities. Review aliases/redirects manually. Podcast identity prefers a stable feed/provider show ID; edition is not required.

Mission fields: objective, client/persona, requested accepted count, required fields, as_of date/timezone, event date bounds, payment policy/minimum/currency, exclusions, tool permissions, maximum authorized cost, elapsed/step limits, progress counts, pending actions, next action and stop reason. If no paid budget is established, use native/public reads and ask for a bounded provider budget only when needed.

Record source-reported attendee numbers as claims; historical editions as historical; a verifier's opinion as a review result. A generic route can be accepted for an exposure campaign if the client permits it, but not called a named decision-maker. For paid-only campaigns, both payment and minimum-fee eligibility must be supported.

The helper's `validate` command checks structural and cross-field invariants only. The agent must inspect sources and decide factual correctness, eligibility, date freshness, topic fit, authenticity and channel ownership. Never label passing JSON validation “verified research.”

For daily operation, reuse stable case_id and existing case paths. Preserve previous facts and source timestamps when a date, fee or contact changes; keep revision history under the client's private workspace. The runner inventories case identities before each cycle and checks new/updated claims against those files. It catches exact duplicate identities, not every renamed event or redirect: resolve those aliases during research. Save JSON using atomic replacement (the distribution's runtime/daily.py exposes atomic_json), so an interrupted write cannot replace a good case with truncated JSON.

Local pipeline transitions are evidence-based. Save a proposed pitch as drafted, client approval as approved, an actual send receipt as contacted, a real response as replied, and a confirmed arrangement as booked. Keep fee/travel/contract facts unknown until established. Never infer those transitions from a dashboard counter or an agent's intention. Daily research can prepare a due follow-up draft using an actual previous sent message; sending still requires its existing authorization. Honor suppression before drafting and preserve client-specific communication history.
