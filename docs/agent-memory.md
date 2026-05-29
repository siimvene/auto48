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
