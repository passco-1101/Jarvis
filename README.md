# Jarvis

A local assistant for Windows. It runs in the background from login, listens only on
`127.0.0.1`, and runs PowerShell commands for you. Risky commands wait for your approval.

## Setup

```powershell
cd C:\Users\Acer\Jarvis
copy .env.example .env      # then add ANTHROPIC_API_KEY to .env (optional, see below)
python -m unittest discover -s tests
scripts\install_autostart.ps1   # starts Jarvis at every login
```

Start it now without logging out: `wscript //B //Nologo start_jarvis.vbs`

## Use

```powershell
python -m jarvis status
python -m jarvis send "!Get-ChildItem C:\Users\Acer\Downloads"   # raw PowerShell, prefix with !
python -m jarvis send "what is my IP address"                    # plain English (needs API key)
python -m jarvis pending                                         # commands waiting for approval
python -m jarvis approve <id>
python -m jarvis deny <id>
```

Plain English works in two ways:
- **No API key (default):** Jarvis calls the Claude Code CLI (`claude -p`), which uses your existing
  Claude login. Requires Claude Code installed and signed in on this PC.
- **API key:** set `ANTHROPIC_API_KEY` in `.env` to use the Anthropic API instead.

Raw `!` commands always work without either.

## Safety

- The daemon listens on `127.0.0.1` only. Nothing outside your PC can reach it.
- Every request needs `JARVIS_TOKEN`, a random secret created in `.env` on first start.
- Commands that look destructive (`Remove-Item`, `del`, `format X:`, `shutdown`, `git push`,
  registry edits, scheduled-task changes, `Invoke-Expression`, ...) are held until you approve them.
  This is a safety net for mistakes, not a sandbox: anything not on that list runs immediately.
- `.env` and `logs/` are git-ignored. Keep secrets only in `.env`.
- Every command and its result is logged to `logs/jarvis.log`.

## Stop or remove

- Stop: `Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | ? CommandLine -match 'jarvis serve' | % { Stop-Process -Id $_.ProcessId }`
- Remove autostart: `Remove-Item "$([Environment]::GetFolderPath('Startup'))\Jarvis.lnk"`

## Layout

- `jarvis/server.py` daemon, HTTP API, approval queue
- `jarvis/risk.py` patterns that need approval
- `jarvis/executor.py` runs PowerShell with no console window
- `jarvis/planner.py` plain English to command via the Anthropic API
- `jarvis/client.py` + `jarvis/__main__.py` command-line client
- `start_jarvis.vbs` hidden launcher; `scripts/install_autostart.ps1` adds the Startup shortcut
