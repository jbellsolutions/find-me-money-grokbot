# Source algorithms and fidelity rules

Primary sources: `speakeragent-api` master `517a038`, newer unmerged `alpha-v0.6.1` `6c2d0c9`, and CLI `cli-agency-release` `714ef03`. Full hashes and function locations are in the distribution's SOURCE-MAP.md and `source-index.json`. Source comments occasionally lag executable behavior; the following distinguishes them.

## Persona → discovery

`profile_utils.build_profile_from_fields` normalizes stored topic `title/abstract` to `topic/description`, loads industries, maps `tagline` to professional title and `location` to target geography. It also carries minimum honorarium, discussion points, website, LinkedIn and notes. Missing fields in the source can default to “General” and “National (US)”; the independent agent preserves unknowns instead.

Conference Alpha derives keywords from non-General topics, then industries; if empty, professional title. It deduplicates case-insensitively. Generic geography strings including US/National are removed from the query suffix. `_build_queries` takes at most eight keywords and emits five templates each, rotating `conference, convention, summit, symposium, congress, forum, annual meeting, workshop, expo` across current/next year.

Search helpers include Tavily, SerpAPI, Serper and Exa according to configuration, seed URLs and Bing fallback. Do not assume every backend ran. v0.6.1 has independent web, Apify directory and Confs.tech lanes. Master additionally has GitHub deadlines and WikiCFP adapters and a conference catalog. These are divergent branches; newest does not mean superset.

Discovery defaults: 200-result ceiling; up to twice that many source-interleaved web candidates; eight scrape workers; 60–365 days out. Unknown dates/formats are retained, known out-of-window dates rejected. Closed CFPs are labeled but retained. Directory entries and technical data have normalization paths; JSON-LD is preferred to loose text for event date, except a listing-specific override in the directory-following path. Product/training detection is imperfect.

The API's v0.6.1 `_run_job` calls discovery with keywords, geography and result cap, not every advanced standalone profile option. Therefore a stored minimum fee or advanced window cannot be assumed to be enforced by this endpoint. The independent agent applies the client's explicit hard constraints itself.

## Conference Alpha relevance versus legacy scoring

Alpha uses a model verdict `MATCH: yes/no` plus one short reason from persona summary and event description. It drops an explicit `no`. Missing key, parse failure and timeout fail open. Retained is not the same as verified relevant. There is no six-factor numerical ranking in this Alpha discovery gate.

The older `scoring.score_lead_with_claude(event_type='Conference')` asks for six 0–10 judgments and calculates:

`round(10 × (0.25 topic_relevance + 0.20 org_type + 0.10 audience_size + 0.10 budget_signals + 0.20 geographic_match + 0.15 timing_fit))`, clamped to 0–100.

Original anchors: topic exact match 10; likely-paying hospital/pharma/major association 10; national 1,000+ audience 10; explicit honorarium 10; exact geography/virtual 10; event 2–6 months away 10, 6–12 months 7, 1–2 or 12+ months 3, past 0. Organization and audience anchors are model heuristics, not facts.

Triage shared by old conference and podcast scores: GREEN ≥65, YELLOW 35–64, RED <35. The old verifier rejects <20, past conference dates and certain geographic mismatches before its model review. Geographic substring heuristics are coarse. Apply actual client geography semantically, not blindly from state abbreviations.

Legacy pay ranges: hospital $5k–15k; pharma $10k–25k; medical association $3k–10k; Fortune 500 $7.5k–20k; midmarket $3k–7.5k; government $2k–5k; university $1.5k–5k; nonprofit $500–2k; unknown $1k–5k. These are hard-coded assumptions, not market research or verified compensation. Preserve them only for explaining historical scores; never present them as an available fee.

The Alpha compensation extractor returns confirmed_paid / likely_paid / expenses_only / confirmed_unpaid / mixed_by_session_type / unknown. Its broad dollar regex can classify attendee tickets as speaker payment. The agent requires explicit speaker-context evidence; a paid flag alone is insufficient. An event's JSON-LD `offers.price` is commonly ticket pricing, not a speaker fee.

## Podcast scoring

Four component inputs, 0–10: topic alignment 70%, recency 15%, reach 10%, guest format 5%. Choose the exact best topic first, then judge its niche fit. Topic anchors: 10 direct niche; 7 recurring subject; 5 adjacent; 0 unrelated. Recency: ≤30 days 10, ≤90 days 7, ≤365 days 3, older 0. Missing/unparseable recency is 0 in the fallback.

Before weighting, adjust topic using confidence `c`:

- `c < .5`: `min(topic, 5)`.
- `.5 ≤ c < .8`: `round(min(topic, 5 + ((c-.5)/.3) × (topic-5)))`.
- `c ≥ .8`: unchanged.

Then `round(10 × (.70 adjusted_topic + .15 recency + .10 reach + .05 guest))`, clamped 0–100. Python round uses ties-to-even; the helper preserves it.

A low-confidence topic of 10 with all other components 10 produces 65 and therefore GREEN. GREEN is not a confidence guarantee. The agent retains confidence separately and reviews questionable fit.

Prompt reach anchors use Listen Score 70+ →9–10, 50–69 →7–8, 30–49 →5–6, below 30 →2–4. Without that, episode counts suggest established/growing/new. Fallback exact reach is 9/7/5/3 for those positive Listen Score bands; without a score, ≥200 episodes 8, ≥50 6, ≥10 4, else 2. Fallback guest score is 7 for guest form/email, else 5. These do not establish that a show interviews guests or has a known listener count.

Fallback keyword matching counts topic words as substrings of title/description, returns confidence .3, and computes the weighted score directly without the model path's confidence adjustment. Label this `fallback_keyword`, not an equally reliable model assessment. A future episode date can also receive full fallback recency credit; the agent checks dates for plausibility.

## Podcast orchestration

Optional internal catalog first, bounded timeout; external PodcastIndex and iTunes plus configured Listen Notes; Apify fallback if fewer than ten unique discoveries. Identity combines feed URL, provider IDs, site URL and show name; metadata is merged. Existing speaker-owned names can be skipped before scoring. Score, discard <20, sort descending with stable input-order tiebreak.

v0.6.1 fills a default target of 20 outreach-ready shows from a ranked pool. Its contact completeness rule is verified email OR at least two nonempty paths among email, LinkedIn, website, booking URL, phone and Twitter. A website plus Twitter can pass this mechanical rule; the personalized agent still checks whether either is a real booking route. Insufficient records receive Needs Contact Research rather than consuming a ready slot. Lower-ranked records may be enriched in background as inactive. The agent does only the batch depth authorized by its mission.

Active hook generation threshold in v0.6.1 is ≥50, even though shared triage turns YELLOW at 35. HC extraction/matching also requires ≥50, its feature flag and speaker signals. A High/Medium HC match uses the connection writer; otherwise a standard hook. Episode analysis/refinement runs only when an HC hook was used, its feature flag is enabled and content is found. Do not treat imports or stale comments as proof the verifier is invoked in every path.

## Contact state and recovery

Master's separate conference catalog canonicalizes event/edition identity and reuses contacts only when its freshness and quality checks pass. Its initial policy is 120 days with minimum tier2; tiers ascend `source`, `tier1`, `tier2`, `tier3`, `fullenrich`. Lower-tier writes must not replace higher-tier contact fields. These are configurable cache heuristics, not evidence that a person still holds a role. The exact 120-day boundary currently has a failing source test. The portable agent preserves source timestamps and rechecks current role/channel before recommending a cached contact.

Case identity is speaker + persona + URL + event name + date, hashed. Current role and owned channel are required for actionable contacts. Generic inboxes/forms are useful fallback outcomes. Up to 20 candidates are retained, with per-candidate evidence and conflicting channels preserved. Channel publication, role support, contact review and email deliverability are separate.

v0.6.1 durable runs save discoveries before enrichment; run ID and stage survive process interruption. Per-case research checkpoints survive display-row replacement. The UI shows a current completed run; historical rows remain stored. Default automatic follow-up admits ten unresolved records, eight strategies per case, five primary pages per source step, two transient source retries, and a reserved browser slot. Retry and lease behavior is more precise in the source worker; the helper is not a replacement for its queue.

Queue priority: future CFP ≤14 days +50, ≤45 +35, later +15; explicitly open +10; WikiCFP/10times +18 with organizer website else +12, other host +10; person +12; email/application form +8; organizer website +5; why-match +4. This is research priority, not fit or conversion probability. Only future deadline values receive deadline points.

## Voice, human connection and writing

HC sequence: speaker signal extraction → guest story → host identity/signal extraction → specific signal matching → connection hook/topic bridge/CTA → optional episode analysis/refinement. Skip weak shared themes. Speaker HC cache is normally 30 days. Voice extractor redacts email/phone, truncates each supplied sample to 800 characters, and excludes samples shorter than 200 from the generation few-shot pool. Store stylistic features; samples do not create biographical facts.

Full-email pipeline: empathetic writer → authenticity checker (average of human, personal, person-to-person, vulnerable, real; threshold 7/10) → up to two revisions → editorial check. Podcast hook review explicitly checks verified detail + supported connection + listener value and bans invented listening/commonality. Some source fallbacks still use unsupported “I've been listening” wording and some review errors retain drafts. The agent explicitly withholds or repairs such claims; review failure is not factual approval.

## Faithful formulas, explicit review corrections

The helper preserves scoring and query mechanics for comparison. New case validation, edition-aware identity, hard client constraints and source review are documented agent-layer corrections. Do not claim bit-for-bit SaaS equivalence, identical model judgments or measured conversion uplift.
