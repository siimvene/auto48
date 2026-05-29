---
id: ms_01KST7SKX865V1303HFFA0YSNT
type: fact
state: active
confidence: 0.7
created: '2026-05-29T16:06:37.223Z'
source: claude
tags:
  - python
  - setup
  - venv
decay_after: '2026-08-27T16:06:37.225Z'
---
# Local Python must be 3.13 (system python3 is 3.9.6, too old)

pyproject requires >=3.12 but /usr/bin/python3 is 3.9.6. Use python3.13 (homebrew, /opt/homebrew/bin/python3.13) to create the venv. Editable install needs modern pip (system venv pip 21.x fails PEP 660 with hatchling) — upgrade pip first: python -m pip install --upgrade pip, then pip install -e '.[dev]'.
