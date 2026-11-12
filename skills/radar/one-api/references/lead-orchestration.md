# Lead orchestration

One API accepts an agent's request through `orchestrator.plan`, saves route alternatives and dispatches one chosen retrieval through `orchestrator.run`. This is a bounded orchestration service with a calling-agent reasoning loop. It is not an unattended worker or a promise to deliver a complete lead list from one sentence.

See the [catalog-driven provider policy](provider-routing-policy.md) for exact evidence thresholds, unit-aware pricing and the four cost/time alternatives.

## Routing algorithm

1. Extract source URL/platform, requested operation, required fields, accessibility and page scope. The request parser uses deterministic rules; the caller can specify the exact URL and scraper specification. Ambiguous sources or selectors remain missing inputs. Group posts and full member enumeration are different jobs.
2. If a request has no source URL, offer bounded source search first; the agent must inspect resulting URLs before a new extraction plan. Email requests offer the existing find/verify routes and require exact identity/domain, LinkedIn identity or a supplied address. Search matches and enrichment are separate from completed lead records. Read the dated complete census, then search the live Treg catalog by the task and refresh the chosen social endpoint contract. Preserve those discovery job IDs. The metadata census is a fallback/reference, not authority to execute additional providers. Unavailable discovery is recorded.
3. Evaluate owned code and free HTTP first. With a valid scraper spec, save immutable JavaScript code and extract through free HTTP. Otherwise inspect the page and let the caller build/test the extractor. Never invent selectors for lead fields or count a title-only page as a lead list.
4. Compare specialist social reads, managed extraction/Firecrawl, and Browser Use Cloud. Match actual operation and available input before choosing. For Facebook group posts or comments, ScrapeCreators is a strong specialist candidate; it is not proof of private-group access or a complete member list. Inspect the full census/live search to compare TikHub, Bright Data, Crawl4AI Cloud, AnyAPI and other documented sources. Unsupported endpoints remain inventory with an explicit adapter gap.
5. Rank matching providers by operation/access fit and measured semantic-hit versus delivery-only evidence tiers, then the selected balanced/cost/speed/reliability preference. Keep native billing units and unknown values explicit. Free/browser route-fit values and setup times remain labeled heuristics, not measured success probabilities. Unknown prices remain unknown. Free is considered first but does not override a materially better chance of useful output. Choose an executable option with sufficient fit; otherwise ask for the missing source/selector/budget or add a reviewed adapter.
6. Optional Jev returns a typed routing advisory under the existing separate TypeSafe monthly ledger. It does not change tool permissions, spend limits or force a route. The calling agent interprets the judgment alongside evidence.
7. Execute one saved option against an existing authorized trial. A plan atomically binds to one route and one trial. One plan has one retrieval page, at most one paid retrieval, stable child IDs, and no automatic paid fallback. Inspect cost and evidence before a new page or fallback plan. The caller owns the total campaign budget across plans; the shared trial ledger enforces the owner's global ceiling.
8. Inspect output. Normalize only observed identities/fields; attach source URL, provider, retrieval time and job ID. Deduplicate on a stable platform ID/profile URL; preserve unknown email/phone and verify contacts separately. Record missing fields, cursor, stale data and blocked sources. A successful HTTP response is not a successful lead task.
9. Reconcile uncertain/pending jobs using their original receipt and supported result tool; do not start another call under a new ID to recover a lost answer. Treg settlement still needs operator reconciliation when native billing is missing. Complete the goal only after the calling agent checks every acceptance criterion.

## Tools

- `accounting.search`: local census search, provider/platform filter, offset/limit pagination.
- `accounting.provider`: provider guide, capabilities/limits and documentation links.
- `accounting.endpoint`: full normalized snapshot inputs/pricing. Read `treg.catalog.get` before paid use.
- `orchestrator.plan`: `request`, optional `url`, `identity` (email, full_name/domain or linkedin_url), `max_cost_usd` (default zero, maximum $1), `required_fields`, `scraper`, `capability`, `preference`, `expected_records`, `time_value_usd_per_hour`, `source_scope`, `use_jev` (default false). No top-level goal ID.
- `orchestrator.get`: `plan_id`; saved options and current receipts.
- `orchestrator.run`: `plan_id`, `option_id`, `trial_id`. No top-level goal ID. Creates a finite child goal and dispatches the selected option once. `complete: false` intentionally leaves evidence review to the agent.
- `treg.social.read`: fixed `endpoint_id`, native `params`, `max_cost_usd`, with top-level running `goal_id`. Eleven explicitly reviewed reads (six ScrapeCreators GET and five AnyAPI POST). ScrapeCreators scope: Facebook group posts and post comments, TikTok/Instagram post comments, LinkedIn person profile and public post search. Live method/path/kind/input/price preflight, native cost ceiling/idempotency, and existing trial reservations apply. AnyAPI scope: Facebook group posts, Instagram/TikTok comments, LinkedIn profile and public post search, body-only. This is not arbitrary proxy access.

## Custom scraper input

Supply `scraper` with a short `name`, `description`, `row_selector`, and `fields` entries `{name, selector, attribute}`. The existing builder validates standard CSS and generates owned JavaScript. Set each lead field explicitly, then run `scraper.test` against representative HTML. The orchestrator saves the same version for free/Firecrawl selection. Browser snippets, standalone Python and Apify exports remain source exports; publication/deployment is a separate authorized operation.

## Quality contract for the calling lead agent

For every accepted record preserve `source_url`, `provider`, `job_id`, `observed_at`, platform/profile identifier, exact observed fields and missing fields. Include a short evidence excerpt for any buying signal. Never infer a person's email, employment, membership or buying intent from a name alone. Track `pages_seen`, `next_cursor`, `records_seen`, duplicates and why collection stopped. Mark coverage partial unless pagination is exhausted for the requested source and authorization. This release returns provider evidence and owned extractor records; it does not implement a universal social-response normalizer, autonomous code author or campaign runner.

## Operational limits

Planning calls live catalog metadata when connected; they create saved read receipts without retrieval spend. Optional Jev is separately billed. One plan's maximum is per retrieval page, not a campaign maximum. At most one paid retrieval can run per plan; new plans require the calling agent to maintain the campaign's remaining budget. There are no automatic retries, provider subscriptions, outbound messages, auth bypasses, account creation or Actor deployment. Browser Use Cloud stays the preferred rendered-browser provider. Existing services stay independent.
