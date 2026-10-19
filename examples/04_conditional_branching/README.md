# Conditional Branching

Demonstrates runtime branching: choosing which job to run based on a variable comparison.

## Run it

```bash
mkdir -p /tmp/pyantz_branching
pyantz pipeline.json
```

After running, check `/tmp/pyantz_branching/config_used.txt` (will say "PRODUCTION") and `/tmp/pyantz_branching/heavy_result.txt` (will exist because `100 > 50`).

Try changing `"environment": "staging"` or `"threshold": "10"` in the variables to see different outcomes.

## What it demonstrates

- **`if_else`** — evaluates `left_side <comparator> right_side` and submits exactly one of two jobs
- **`conditionally_execute`** — like `if_else` but with no `if_false` branch; does nothing when condition is false
- **Inline job configs** — `if_true` / `if_false` are full job configs embedded inside the parameters; they are parsed and validated at startup
- **Comparators** — supported: `=`, `==`, `<`, `<=`, `>`, `>=`, `!=`, `~=`
- Variables in comparands: `%{environment}` and `%{threshold}` are replaced before comparison

## Try it with different settings

Change `"environment": "development"` → only the development config file is written.

Change `"threshold": "10"` → `10 > 50` is false so `heavy_result.txt` is not created.
