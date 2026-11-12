Source: npm `orgo@1.0.22` (last v1; repo git+https://github.com/spencerkinney/orgo-cli.git, not publicly readable at capture). Surface read from the package's index.d.ts. Docs: https://docs.orgo.ai/guides/claude-computer-use. Summarized.

# TypeScript SDK

IMPORTANT: from `orgo@2` the npm package `orgo` is the **CLI** (bin `orgo`, 2.5.0 latest; no library exports). The TypeScript library lives in `orgo@1`: `npm install orgo@1`. No separate official TS REST SDK was found; for current endpoints, call the REST API with `fetch` (docs' quickstart does this) or use the CLI/MCP. Related official packages: `orgo-vnc` 0.3.0 (React embed, `ComputerDisplay`; OrgoAI/orgo-vnc) and `orgo-convex` (Convex component; OrgoAI/orgo-convex). Versions before 1.0.22 default to 2 GB RAM, which the API rejects.

All methods are async and camelCase. Constructors are private: use `static create()`.

## Exports
`Computer`, `Project` (+ `createComputer`, `createProject`, `createWorkspace` helpers), errors `OrgoError`, `ApiError(statusCode, response)`, `ConfigError`, types `ComputerConfig`, `ComputerInfo`, `ComputerStatus`, `ExecResponse`, `ProjectInfo`, `PromptMessage`, `PromptOptions`, `ScreenshotOptions`, `ScrollOptions`, stream response types.

## Computer
```ts
Computer.create({ project?, workspace?, name?, computerId?, apiKey?, baseApiUrl?, ram?, memory?, cpu?, os?, gpu?, image?, verbose? }): Promise<Computer>
```
ram 1|2|4|8|16|32|64; cpu 0.5..16; os linux|windows; gpu none|a10|l40s|a100-40gb|a100-80gb. Key from `apiKey` or `ORGO_API_KEY`.

Methods: `status()`, `restart()`, `destroy()`, `leftClick(x,y)`, `rightClick(x,y)`, `doubleClick(x,y)`, `drag(sx,sy,ex,ey,button?,duration?)`, `scroll(direction?, amount?, x?, y?)`, `type(text)`, `key(key)`, `screenshot({format:'base64'|'buffer'})`, `screenshotBase64()`, `bash(cmd): string`, `exec(code, timeout?): ExecResponse {success, output, error?, error_type?, timeout?}`, `wait(seconds)`, `startStream(conn)`, `stopStream()`, `streamStatus()`, `prompt(instruction, {provider, model, displayWidth, displayHeight, callback, thinkingEnabled, thinkingBudget, maxTokens, maxIterations, maxSavedScreenshots, systemPrompt, apiKey}): PromptMessage[]`. Props: `computerId`, `name`, `projectId`, `projectName`, `url`.

## Project
`Project.create({name?, apiKey?, baseApiUrl?})`; `.status()`, `.destroy()`, `.listComputers()`, `.getComputer(name?)`, `.info`, `.id`, `.name`.

## Example
```ts
import { Computer } from 'orgo';   // orgo@1
const c = await Computer.create({ workspace: 'demo', ram: 4, cpu: 1 });
await c.leftClick(640, 360);
await c.type('hello'); await c.key('Enter');
const png = await c.screenshot({ format: 'buffer' });
console.log(await c.bash('uname -a'));
await c.destroy();
```
