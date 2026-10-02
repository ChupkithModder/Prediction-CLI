# Prediction CLI

A quiet, OpenCode-inspired terminal **frontend** for educational BTC/USD 15-minute forecast summaries. Big centered logo, short updates, a slash-command prompt, and a tiny forecast-score/accuracy/skips strip. Details stay behind `/stats` and `/logs`.

**The backend has been removed.** This client does not forecast, run models, schedule jobs, calculate scores, maintain learning memory, connect accounts, or place orders. There is no profit/bankroll/wager tracker or betting integration. Your own external educational forecast backend can provide typed local JSON; this app displays it. Start/Stop emit optional local request messages and do not execute anything.

## Downloads and launch

Python **3.10+** is required. These are portable Python apps, not standalone native binaries. No Python packages, credentials, signup, paid dependencies or backend are bundled.

- macOS: unzip the macOS portable ZIP and open `Prediction CLI.command`
- Linux: unzip the Linux portable ZIP and run `./prediction-cli` in a terminal
- Windows: unzip the Windows portable ZIP and open `Prediction CLI.cmd` in Windows Terminal

Install Python from https://www.python.org/downloads/ if needed. Alternatively, in the unzipped folder:

```sh
python3 prediction-cli.pyz
```

Windows can use `py -3 prediction-cli.pyz`. If macOS blocks an unsigned downloaded launcher, run the Python command in Terminal rather than bypassing a security warning. Recommended terminal: at least 70 columns × 24 rows.

The default screen is **disconnected**. No backend runs behind it. A safe offline interface preview:

```sh
python3 prediction-cli.pyz --demo
python3 prediction-cli.pyz --demo status
```

Demo updates are explicitly synthetic. No model or backend runs, and no accuracy or forecast-score result is invented.

## Slash commands

- `/start`: Write a start request when a request output file is configured
- `/stop`: Write a stop request when a request output file is configured
- `/model [id]`: List or select a backend-declared model
- `/stats`: Backend-reported metrics and source notes
- `/logs`: External events; arrows scroll
- `/export`: Save the displayed events as a CSV locally
- `/help`, `/home`, `/quit`: Help, summaries, close

A request is only a request. The screen remains in the last backend-reported state until a new snapshot/event acknowledges the change. Closing this frontend does not control an external backend.

## Plug in your own forecast backend

The interface is local-file JSON only. It makes no network requests and never launches a subprocess. Your backend owns forecasting, model execution, scheduling, deadlines, persistence and metric definitions. It should write snapshots atomically using temporary-file replacement. Models and metrics are backend-declared, not independently verified by this client.

```sh
python3 prediction-cli.pyz --snapshot /path/to/snapshot.json
python3 prediction-cli.pyz --snapshot /path/to/snapshot.json --requests /path/to/requests.jsonl
python3 prediction-cli.pyz --snapshot /path/to/snapshot.json status --json
python3 prediction-cli.pyz --snapshot /path/to/snapshot.json export --output report.csv
```

Snapshot schema:

```json
{
  "schema": "prediction-cli-snapshot-v1",
  "symbol": "BTC/USD",
  "horizon_seconds": 900,
  "mode": "external",
  "status": "idle",
  "model": "your-model-id",
  "models": ["your-model-id"],
  "as_of": 1790899200,
  "metrics": {"forecast_score": null, "accuracy": null, "skipped": 0},
  "events": []
}
```

Use `mode: "synthetic"` for every mock/demo snapshot. `as_of` and event `at` are UTC epoch seconds. `status` is `disconnected`, `idle`, `running`, `stopped` or `error`. Model identifiers are single tokens of letters, digits, `.`, `_`, `:` or `-`, at most 80 characters. Accuracy and normalized forecast score are 0–1 or null; they are displayed exactly as supplied. Scores may be absent/unknown; the client never computes or substitutes them.

Events have unique `id`, `type`, `at`, `model` and a short `summary`. Supported types: `forecast`, `abstain`, `skip`, `outcome`, `status`. Optional fields are `p_up` (0–1 or null), `decision` (`up/down/abstain`), `outcome` (`up/down/flat/void`), and `status`. Forecast events require directional decision and p_up; outcome events require outcome. Summary is plain text, 1–400 characters; terminal control characters are rejected. No hidden reasoning is requested.

```json
{"id":"window-1","type":"skip","at":1790899200,"model":"your-model-id","summary":"Weak evidence; skipped this window."}
```

For JSONL, use `--events /path/to/events.jsonl` instead of `--snapshot`. Each event line additionally has `schema: "prediction-cli-event-v1"`. A status event with a `status` field updates the displayed backend state. Snapshot/event files must be <=1 MB and <=200 events; rotate them externally. Duplicate keys/ids, nonfinite numbers, invalid fields and terminal escape sequences are rejected. Unknown fields, including financial execution/tracker fields, are unsupported. A stale or future snapshot is labeled; unreadable/invalid input displays an error and retains the last valid view.

## Optional control requests

Only an explicit `--requests PATH` enables writing local control requests. Without it, `/start` and `/stop` report that no backend control file is configured. Nothing is executed by the frontend, even with it configured. Your own educational forecast backend may consume the file, deduplicate by `request_id`, then report its actual state through the input protocol.

```json
{"schema":"prediction-cli-control-v1","request_id":"opaque-unique-id","requested_at":1790899200,"command":"start"}
```

Commands are `start`, `stop` or `model`. A model-selection request includes `model`. `/start` may include the current backend-declared selection. These are forecast-control messages, not account/order/payment commands. There is no executable adapter or private hosted endpoint.

## Privacy and exports

No credentials, private Site URLs, service tokens, personal history, local learning files or datasets are included. This client doesn't save backend state automatically. CSV/JSON exports are user-requested local files; existing files are never overwritten. CSV protects against spreadsheet formula injection. Exports contain only the validated view/events, without local input/output paths. Review your backend summaries before sharing them.

## Build and verification

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q prediction_cli
python3 build.py
python3 dist/prediction-cli.pyz --demo status --json
```

Source-mode launch: `python3 -m prediction_cli`. Build creates one `.pyz`, portable macOS/Linux/Windows ZIPs, a source ZIP and SHA256SUMS. POSIX launchers are marked executable inside bundles even if a GitHub checkout lost those file modes.

Linux runtime and real PTY slash-input tests are run locally. macOS/Windows paths and launchers are statically reviewed; runtime claims depend on the corresponding CI results. Native signed executables are not provided. No external backend/provider integration is claimed tested.
