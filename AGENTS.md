# AGENTS.md

Jinja2-based code/template generator built on Django 5.2. Accepts ZIP-uploaded template packages, renders output files by evaluating Jinja2 templates against user-provided JSON context. Output goes to `toutput/`.

## Commands

```
python manage.py runserver                           # dev server
python manage.py test                                # all tests
python manage.py test main                           # single app
python manage.py test main.tests.TestClass.test_method  # single test
python manage.py makemigrations && python manage.py migrate  # migrations
```

## Architecture

- `jinjaGenerator/` — Django project package (settings, root URL conf)
- `main/` — Single Django app with all business logic
- `main/renderer/` — Core rendering engine (Python package, not a Django app)
  - `renderer.py` — Orchestrates rendering: creates output folder, walks `project/`, delegates to Jinja2 or copies static files
  - `loader.py` — Builds Jinja2 `Environment`: auto-discovers and dynamically imports Python files from template subfolders to register filters, tests, and globals
  - `wildcard_resolver.py` — Resolves `%...%` wildcards in file paths (dot-notation, filter piping with `$`, list expansion, recursive multi-wildcard resolution)
  - `defaults.py` — Provides `render_fragment` global for rendering partials from `fragments/`

## API Endpoints

- `POST /template/load` — Upload a ZIP file, extracts into `templates/<name>/`
- `POST /template/render?template_name=<name>` — JSON body as context, renders to `toutput/<name>/`

## Template Package Structure

```
templates/<name>/
  project/        # REQUIRED — files to render/copy to output
  filters/        # Python files → Jinja2 filters ({{ value|myfilter }})
  tests/          # Python files → Jinja2 tests ({% if value is mytest %})
  fragments/      # Jinja2 partials via render_fragment()
  macros/         # Standard Jinja2 macros via {% import %}
  <other>/        # Any other folder → Python exports added to Jinja2 globals
```

Only `project/` is required. Other folders are optional and auto-discovered by `loader.py`.

## Rendering Rules

- `.jinja`/`.j2` files → rendered through Jinja2, extension stripped from output (e.g., `t1.html.jinja` → `t1.html`)
- All other files → copied as-is

## Wildcard Path Resolution (`%expression%`)

File/directory names in `project/` support `%expression%` wildcards that expand against JSON context.

Simple substitution:
  `t3%name%.py` + `{"name": "john_doe"}` → `t3john_doe.py`

Dot-notation traversal:
  `t4.%object.name%.%object.value%.html.j2` + `{"object": {"name": "a", "value": 2}}` → `t4.a.2.html`

List expansion (one output per item):
  `models/%models.name%.out.j2` + `{"models": [{"name": "user"}, {"name": "post"}]}` → `models/user.out` AND `models/post.out`

Filter chaining with `$`:
  `%models.name$uppercase%` → `USER`, `POST`
  `%models.name$truncate(3)%` — filters take arguments
  `%models.name$filter1$filter2%` — multiple filters chain left-to-right

Global function calls in paths:
  `controller%get_non_hidden_models().name%/` — calls a global function, then expands `.name`

`_path` variable: inside rendered templates, `_path` is a dict of resolved wildcard values for that file.

## Custom Python Extensions

**Filters** (`filters/`): All non-underscore callables become Jinja2 filters. Support `@pass_context`:
```python
from jinja2 import pass_context

@pass_context
def context_aware_filter(ctx, value, param1):
    return f"{value} (time: {ctx['current_time']})"

def uppercase(value):
    return value.upper()
```

**Tests** (`tests/`): Same loading as filters. Callables become Jinja2 tests:
```python
def adult(age):
    return age >= 18
# Usage: {% if value2 is adult %}
```

**Globals** (`other/` and any non-reserved folder): Exports (functions + constants) added to Jinja2 globals:
```python
DATA = "abc"          # → {{ DATA }}

@pass_context
def get_non_hidden_models(ctx):
    return [m for m in ctx['models'] if not m.get('hidden', False)]
```

**Fragments** (`fragments/`): Context-aware sub-templates that inherit the full render context:
```jinja
{{ render_fragment('simple.txt', {'a': 2}) }}
```

**Macros** (`macros/`): Standard Jinja2 macros, isolated to their parameters only:
```jinja
{% import 'macros/form' as macros %}
{{ macros.render_input('[NAME]', label='[LABEL]') }}
```

## Conventions

- `manage.py` patches `sys.modules['sqlite3']` with `pysqlite3` before Django loads — preserve this shim
- CSRF is disabled (commented-out middleware + `@csrf_exempt`). Endpoints accept raw POST
- No REST framework — plain Django function views returning `JsonResponse`
- `Template` model (`main/models.py`) stores only `name` and `folder` path; actual content is on filesystem under `templates/`
- Private functions use `__` prefix (e.g., `__create_output_folder`)

## Maintaining These Instructions

Template structure and rendering capabilities are actively evolving. When renderer modules or template conventions change (new folder types, wildcard syntax, built-in globals), update `.github/copilot-instructions.md` and this file.
