# Custom Jobs

Write your own job functions and use them in a pipeline alongside built-in jobs.

## Run it

The pipeline references `examples.10_custom_jobs.my_jobs`, so run from the repo root so Python can find the module:

```bash
cd /path/to/pyantz
mkdir -p /tmp/pyantz_custom
python -m pyantz examples/10_custom_jobs/pipeline.json
```

After running:
- `/tmp/pyantz_custom/word_count.txt` — contains `9` (words in the input)
- `/tmp/pyantz_custom/done_flags/` — contains `alpha.done`, `beta.done`, `gamma.done`, `delta.done`

## The three patterns

### 1. Simple job — `@add_parameters` + `@no_submit_fn`

```python
class WordCountParams(BaseModel):
    input_file: Path
    output_file: Path


@add_parameters(WordCountParams)
@no_submit_fn
def word_count(params: WordCountParams) -> bool:
    ...
    return True
```

- `@add_parameters(MyModel)` — validates parameters against the Pydantic model at runtime; registers the function in the API
- `@no_submit_fn` — removes the `submit_fn` argument so your function only receives `params`
- Return `True` = success; `False` = failure (stops dependent jobs)

### 2. Dynamic fan-out — using `submit_fn`

```python
@add_parameters(FanOutParams)
def fan_out(params: FanOutParams, submit_fn: SubmissionFnType) -> bool:
    for item in params.items:
        job = JobConfig(function="...", parameters={...})
        submit_fn(job)
    return True
```

- Drop `@no_submit_fn` to receive the `submit_fn` callable
- Call `submit_fn(job_config)` to enqueue new jobs dynamically
- Child jobs inherit the parent's variable context automatically
- Downstream jobs that depended on `fan_out` will wait for all submitted children before running

### 3. Purely custom (no decorator)

```python
def my_raw_job(params: dict, submit_fn) -> bool:
    value = params["some_key"]
    ...
    return True
```

No validation, no API registration, but works fine.

## Packaging custom jobs

For production use, put your jobs in a proper package:

```
myproject/
  jobs/
    __init__.py
    analysis.py     # contains @add_parameters functions
  configs/
    pipeline.json   # references "myproject.jobs.analysis.my_func"
```

Install with `pip install -e .` and reference as `"myproject.jobs.analysis.my_func"`.
