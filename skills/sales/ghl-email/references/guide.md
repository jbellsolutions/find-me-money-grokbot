# Email campaigns and nurture sequences

Status: documentation-derived; sending and scheduling need account acceptance tests.
Sources: [templates versus campaigns](https://help.gohighlevel.com/support/solutions/articles/48001215255-email-templates-vs-email-campaigns),
[send/schedule](https://help.gohighlevel.com/support/solutions/articles/48001215263-send-or-schedule-an-email-campaign),
[preview/test](https://help.gohighlevel.com/support/solutions/articles/48001215382-preview-and-test-your-email-campaigns-templates).

## Choose the delivery model

Use `ghl hub operations --domain emails` for documented template operations and
scheduled-email reads. Inspect `emails:create-template` and `emails:update-template`
schemas before use; template payloads have distinct types. A template is reusable
content. A broadcast campaign defines recipients and timing. A nurture sequence
is usually workflow actions and waits. Conversation messages are individual sends.
Do not substitute a message loop for a properly configured bulk email campaign.

Inputs: sender and reply-to, subject/preheader, content/template, audience filters and
exclusions, timezone, schedule and any batching, plus desired final state. Confirm
that the account's sending service/domain is configured. Use opt-in lists and honor
suppression/DND/unsubscribe state; these directly affect valid delivery.

## Dashboard procedure

1. Confirm the location and open Marketing → Emails. Select Templates or Campaigns
   as appropriate. Search before creating a new asset.
2. Build/open the template or create the campaign from a template/blank layout.
   Set the internal name and edit content. Use the merge-field picker and suitable
   fallback copy. Include the account's required unsubscribe/footer content.
3. Configure subject, preheader, sender identity and reply-to using the actual send
   settings. Do not assume the visible template name is the subject line.
4. Preview desktop/mobile and send a test only to controlled addresses. Verify
   merge values with a real test contact where preview does not resolve them.
   Check links, tracking parameters, images, alt text and plain text when available.
5. In the campaign's recipient settings choose the specified lists/segments/tags.
   Review exclusions, suppression and the resulting count. Record the selection
   rules, not just the count; dynamic audiences can change before send time.
6. Choose the intended send mode: draft, immediate, schedule or batch. Confirm the
   displayed timezone and exact time. Review the send summary against the requested
   audience and timing before the final execution action.
7. If launch is authorized, send/schedule and inspect the resulting status. Reload
   and confirm it persisted. Record campaign ID, scheduled time, timezone and audience.
8. Review available delivery/bounce statistics after a test or launch. Investigate
   provider failures rather than resending the same campaign blindly.

For multi-message nurture, follow the workflow skill: trigger, audience filters,
message actions, waits, reply/exit conditions and per-branch tests. For an already
scheduled campaign inspect its state and current change/pause rules before editing.
A send may already have started; cancellation does not recall delivered mail.
