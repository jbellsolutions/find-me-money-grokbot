# Weekly usage audit (report only)

Runs once a week inside an existing run (the lead's Monday evening report). It changes nothing. It writes one report and puts the top three changes in the owner's queue.

1. **Usage reading.** Read the % used and the reset date from the usage screen if you can see it; if not, ask the owner once in the morning brief. Add a row to `log/usage-ledger.md`.
2. **Where it went.** If the owner dropped a usage export into `data/usage/`, run `python3 scripts/usage_csv.py data/usage/<file>.csv` and copy the top lines. Never paste the export into chat.
3. **Routines.** List every routine with its schedule and runs per week, and how many of last week's runs found anything. Label each one:
   - **KEEP**: it earns its runs.
   - **SLOW**: give it a slower cron, or limit it to working hours in the bot's time zone.
   - **EVENT**: it should start on a webhook or a file instead of a clock.
   - **CHANGE**: same job, cheaper trigger or a smaller read.
   - **RETIRE**: nothing useful in 7 days; propose pausing it, never deleting.

   Anything more often than every 3 hours that mostly ended `[SILENT]` defaults to SLOW. Flag two routines of one bot that start under 5 minutes apart.
4. **Instructions weight.** Count the words in the master prompt, each role section and the saved memory. Every turn and every run re-reads them. Flag duplicated rules, stale facts and anything a file could hold instead ("see context/x.md").
5. **Reading habits** (from last week's `log/` and run notes). Count browser sessions, screenshots, whole-PDF reads and whole-page reads. For each, name the usage-saver script that would have answered instead.
6. **Repeat jobs.** Any job done the same way three or more times: propose a script.
7. **Skills, plugins, memory.** Count private skills (flag over 90), unused plugins, and duplicate or stale memory entries.
8. **Heavy chats.** Flag any chat whose history has grown long or that drags in big files every turn. Propose the reset in `RESET.md`.
9. **Report.** Write `requests/<owner>/usage-<date>.md` with:
   - the reading;
   - the routine table with labels;
   - the top three changes, the saving each should bring, and what each needs (a yes, a key, a sign-in).

   Nothing is changed, paused, deleted or bought without the owner's yes.

**When usage is nearly gone mid-week.** Propose pausing every routine except the lead's, then re-enabling KEEP routines first and SLOW routines next, one at a time, with a reading between each. Propose it; don't do it.

End with one line for the scoreboard: `usage: <pct>% used, <n> flags, top change: <one line>`.
