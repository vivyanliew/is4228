# Research Knowledge Base

This folder stores research sources and structured summaries for Agent 2 (Strategy Generation Agent).

## Layout

- `paper_index.json`
  - Main structured metadata file used by the agent.
- `papers/`
  - Store the original PDFs or notes here.
- `.gitkeep`
  - Keeps the `papers/` folder in version control when empty.

## Recommended workflow

1. Add a paper PDF into `papers/`.
2. Create one matching entry in `paper_index.json`.
3. Summarize the paper into:
   - `summary`
   - `key_findings`
   - `parameter_guidance`
   - `works_best_when`
   - `fails_when`
4. Tag whether the idea is currently:
   - `backtestable: true`
   - or `backtestable: false`

## Notes

- `backtestable: true` means the strategy maps to a live strategy your current backtest engine already supports.
- `backtestable: false` means it is an experimental idea that still needs implementation before Agent 3 can run it.
- Keep summaries short, grounded, and factual.
- Avoid copying large chunks of paper text. Prefer concise paraphrased notes.

