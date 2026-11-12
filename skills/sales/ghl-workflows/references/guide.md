# Build and operate a workflow

Status: documentation-derived; authenticated execution remains to be verified.
Sources: [builder walkthrough](https://help.gohighlevel.com/support/solutions/articles/155000001254-workflow-builder-walkthrough),
[triggers](https://help.gohighlevel.com/support/solutions/articles/155000002292),
[actions](https://help.gohighlevel.com/support/solutions/articles/155000002294).
Read the relevant action/trigger article from the local corpus before configuring it.

## API boundary

`ghl hub operations --domain workflows` exposes workflow listing. Enrollment/removal
operations are in contacts: search `ghl hub operations "workflow"`. Enrollment starts
an existing automation; it does not create its graph. Imported `--experimental`
commands use an unofficial full-login Firebase client and are excluded from hub MCP.
Use the supported browser path for routine authoring.

## Inputs

Describe the event, trigger filters, audience, re-entry policy, timezone/business
hours, action order, conditions, waits, goal/exit behavior, and desired final state.
Include message sender identities and external integrations where used. Build a
small explicit graph locally first: each branch needs a destination and terminal state.

## Dashboard procedure

1. Confirm the location, then open Automation → Workflows. Search for the intended
   workflow before creating anything. For updates record its URL and existing state.
2. Choose Create Workflow and the appropriate start/template option. Name and organize
   it. Keep a new workflow in draft while building.
3. Choose Add New Trigger, select the event and configure filters. Save the trigger.
   Multiple triggers independently enroll contacts; they are not a combined AND filter.
4. Add actions with the canvas `+` controls. Select each action by its current UI label,
   configure its required fields, give it a clear name and save it. Use the merge-field
   picker for contact values. Do not paste guessed variable names.
5. Configure each conditional branch and its fallback. Add waits with the correct
   timezone/window. Inspect connected-account selection for integration-powered steps;
   changing an account can reset dependent fields. Save every configured node.
6. Open workflow settings. Set re-entry, stop-on-response and time settings according
   to the design; labels/availability vary by workflow type. Do not assume defaults.
7. Save and reopen. Check every edge, branch and action. Turn off Stats View when
   editing; it prevents edits in the documented builder.
8. Use Test Workflow with a controlled contact where available. Then test the actual
   trigger event because a test run may not exercise real enrollment/filter behavior.
   Check history, branch decisions, wait scheduling and test deliveries. Confirm a
   contact that should be excluded does not enroll.
9. Set Draft/Publish to the requested state and verify it after reload. Publish only
   within the user's requested launch scope. Record the workflow ID and test results.

## Recovery and scale

For an existing live workflow inspect in-progress contacts before changing waits,
branches or actions. Test a duplicate/draft if the change could affect current paths.
Use version history when applicable and verify rollback semantics in current docs.
A draft JSON graph is a design artifact, not a deployed workflow. Build once, validate,
and use supported snapshot loading or documented template mechanisms for reuse;
check snapshot exclusions and target-specific credentials before rollout.
