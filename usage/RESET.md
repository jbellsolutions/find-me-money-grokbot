# Reset a heavy bot (owner-approved only)

A bot that has run for weeks carries its whole chat history, and much of it is old. A fresh copy that keeps only what matters reads far less each turn (one cited report: 158.8K per turn for the old bot against 35.7K for its clean copy; measure your own with the ledger).

Only on the owner's yes, and never delete the old bot in the same week:

1. Ask the old bot: "List the rules, facts, decisions and open jobs that must survive a fresh start. Leave out anything already in the repo or the workspace files." Save the answer to `context/reset-<bot>-<date>.md`.
2. Put the must-keep rules in the bot's description: it always carries over to a duplicate. The owner duplicates the bot (settings, skills and description carry over; chat and memory don't), and the copy reads `context/reset-<bot>-<date>.md` and saves what matters to memory.
3. Check: ask both bots three questions about current work; the new one must answer from the file and the workspace.
4. Keep the old bot hidden (unpinned) for a week. Delete it only on the owner's separate yes.
5. Write the before and after usage readings in `log/usage-ledger.md`.
