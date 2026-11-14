Source: PyPI `orgo` 0.0.47 (author "Orgo Team", docs https://docs.orgo.ai; no public GitHub source repo found: PyPI lists no repo URL and OrgoAI/orgo-py was not found). Surface read from the published wheel. Summarized, not copied.

# Python SDK (`pip install orgo`)

Thin synchronous wrapper over the REST API (`requests`, Pillow for screenshots). Key from `api_key=` or env `ORGO_API_KEY`; base URL default `https://www.orgo.ai/api`, override with `base_api_url=`. Versions before 0.0.47 default to 2 GB RAM, which `POST /computers` rejects (400). The SDK only covers create/destroy/restart plus actions; for start/stop/resize/clone/files/secrets/public URLs/etc. use REST (see site/api-reference/) or the CLI/MCP. Its stream methods call `/computers/{id}/stream/*`, which are absent from the current 2.0.0 spec (treat as legacy).

## Exports
`Computer`, `Project` (alias `Workspace`), `Template` (alias `Forge`, deprecated).

## Computer
```python
Computer(project=None, workspace=None, name=None, computer_id=None, api_key=None, base_api_url=None,
         ram=None, memory=None, cpu=None, os=None, gpu=None, template=None, image=None, verbose=True)
```
- ram: 4/8/16/32/64 GB; cpu: 0.5/1/2/4/8/16; os: "linux"|"windows"; gpu: "none","a10","l40s","a100-40gb","a100-80gb". Omit ram+cpu and Orgo picks (4 GB/1 vCPU, or template size).
- `project`/`workspace` name: connects or creates the workspace, then creates a computer in it. `computer_id=`: attach to an existing computer. No args: new workspace + computer.
- Lifecycle: `status()`, `restart()`, `destroy()`.
- Mouse: `left_click(x,y)`, `right_click(x,y)`, `double_click(x,y)`, `drag(sx,sy,ex,ey,button="left",duration=0.5)`, `scroll(direction="down", amount=3, x=None, y=None)` (pass both x,y or neither; Windows rejects x/y).
- Keyboard: `type(text)`, `key(key)` (e.g. "Enter", "ctrl+c").
- Screen: `screenshot() -> PIL.Image`, `screenshot_base64() -> str`.
- Code: `bash(command) -> str` (output), `exec(code, timeout=10) -> dict` (Python), `wait(seconds)`.
- Streaming (RTMP): `start_stream(connection)`, `stop_stream()`, `stream_status()`.
- AI loop: `prompt(instruction, provider=None ("orgo" default | "anthropic"), verbose=True, callback=None, model="claude-sonnet-4-6", display_width=1024, display_height=768, thinking_enabled=True, thinking_budget=1024, max_tokens=4096, max_iterations=100, max_saved_screenshots=3, system_prompt=None, api_key=None) -> list[messages]`.
- Attributes: `computer_id`, `name`, `project_id`, `project_name`, `url`.

## Project / Workspace
`Project(name=None, api_key=None, base_api_url=None)` get-or-create by name; `.status()`, `.start()`, `.stop()`, `.restart()`, `.destroy()`, `.list_computers()`, `.get_computer(name=None)`, `.id`, `.name`.

## Template (image builder, legacy)
`Template(name, workspace=None, ...)` with chainable `.run(cmd)`, `.copy(src,dest)`, `.env(k,v)`, `.workdir(path)`, `.clone(repo_url, dest="/repo")`, `.build(context=".") -> image ref`, `.image_ref`. Then `Computer(template=tpl_or_name)`. The newer YAML template system (orgo.ai/v1) is REST/CLI only: see site/guides/templates/.

## Example
```python
from orgo import Computer
c = Computer(workspace="demo", name="agent-1", ram=4, cpu=1)
c.bash("uname -a")
c.left_click(640, 360); c.type("hello"); c.key("Enter")
img = c.screenshot()          # PIL image
c.exec("print(1+1)")
c.destroy()
```
