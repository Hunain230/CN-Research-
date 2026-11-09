# Phase 6 research dashboard

`index.html` is a self-contained static dashboard generated from aggregate metrics and the Module 6B gate audit. It uses no external JavaScript, network calls, API keys, or additional Python packages. It contains no raw rows, row-level predictions, evaluator mappings, organization identifiers, or credentials.

## Preview locally

Open `index.html` in a browser. To serve it locally instead, run from the project root:

```powershell
py -m http.server 8765 --directory dashboard
```

Then open `http://127.0.0.1:8765`.

## Rebuild

After aggregate source reports change, rebuild with:

```powershell
.\.venv\Scripts\python.exe -m src.phase6g_dashboard --root .
```

Review the visible exploratory/data limitations before publishing. Deploy the `dashboard/` directory to a static hosting service. This project turn generated a deployable artifact but did not publish it to an external hosting account.
