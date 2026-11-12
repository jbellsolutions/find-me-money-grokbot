# The computer-use loop on Orgo

Orgo's action endpoints are the hands; your model is the eyes and brain. Orgo documents the same loop for Claude, OpenAI and Gemini computer use (`docs/site/guides/claude-computer-use.md`, `openai-computer-use.md`, `gemini-computer-use.md`).

## Loop

1. `screenshot` (scale 0.5 is enough to read most screens and saves tokens).
2. Decide one action from what's on screen.
3. Act: `click`, `type`, `key`, `scroll`, `drag`.
4. `wait` 1-2 s if the page loads, then screenshot again and check that the action did what you meant.
5. Stop when the goal is met or when a blocker appears (sign-in, 2FA, CAPTCHA, payment, an error page). Hand blockers to the owner.

## Coordinates

- Click coordinates are always in the computer's full resolution. A screenshot taken with `--scale 0.5` must have its coordinates doubled.
- `scroll` moves the pointer to X,Y before every wheel click; leaving X,Y out scrolls whatever is at 0,0.
- `type` waits at most 30 s; for long text, paste through the clipboard (`bash "printf %s '...' | xclip -selection clipboard"` then `key ctrl+v`) or write a file.

## Screens

A computer can carry several screens (`/computers/{id}/screens`). Each action takes `--screen <id>`; leave it out for the boot screen. GrokBot gives each bot its own screen on a shared computer.

## Prefer the terminal

Clicking is slow and fragile. If the job can be done in `bash` (curl, a CLI, a script, Playwright), do it there. Use the screen for sites that need a real logged-in Chrome, for checking what a human would see, and for proof screenshots.

## Live view and takeover

The dashboard (orgo.ai) shows the live screen. VNC: `GET /computers/{id}/vnc-password` (credential: never print it). Apps like GrokBot stream the VNC websocket with "take over / give back".
