# Agent Memory

Persistent log of mistakes and their fixes, per `.cursor/rules/common/agent-memory.mdc`.
Read this before starting work; append corrections after fixing a mistake or deprecation.

Keep entries general and reusable — not one-off, file-specific details.

## Format

```markdown
### Mistake: [Short Description]
**Wrong**:
[incorrect code or logic]

**Correct**:
[corrected code or logic]
```

---

<!-- Add entries below. -->

### Mistake: arq WorkerSettings.redis_settings defined as an instance @property
arq reads `redis_settings` off the **class** (`arq auto48.workers.X.WorkerSettings`),
so a `@property` hands arq the descriptor object, not a value → the worker
crash-loops with `AttributeError: 'property' object has no attribute 'host'`.
The API stays up (it enqueues via its own pool), so this hides unless you check
worker logs. Found in production on first deploy.

**Wrong**:
```python
class WorkerSettings:
    functions = [process_image]

    @property
    def redis_settings(self) -> RedisSettings:
        return RedisSettings.from_dsn(get_settings().redis_url)
```

**Correct**:
```python
class WorkerSettings:
    functions = [process_image]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)  # class attribute
```

### Mistake: pydantic-settings list[str] env var crashes app on startup
A `list[str]` settings field is **JSON-decoded** by pydantic-settings' env source
*before* any `field_validator(mode="before")` runs. So setting a comma-separated
env value (e.g. `AUTO48_CORS_ORIGINS=https://kekec.ee,https://www.kekec.ee`)
raises `SettingsError: error parsing value for field ...` and the app won't boot —
silent until something actually sets the env var (e.g. production). Annotate the
field with `NoDecode` so the raw string reaches the CSV-splitting validator.

**Wrong**:
```python
cors_origins: list[str] = [...]
@field_validator("cors_origins", mode="before")  # never runs for a non-JSON env string
```

**Correct**:
```python
from pydantic_settings import NoDecode
cors_origins: Annotated[list[str], NoDecode] = [...]
@field_validator("cors_origins", mode="before")  # now receives the raw CSV string
```
