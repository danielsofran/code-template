# Copilot Instructions

## Project Overview

This is a **Jinja2-based code/template generator** built on Django 5.2. It accepts ZIP-uploaded template packages, stores them on disk, and renders output files by evaluating Jinja2 templates against user-provided JSON context. The rendered output goes to `toutput/`.

## Commands

```bash
# Run the dev server
python manage.py runserver

# Run tests
python manage.py test
python manage.py test main                    # single app
python manage.py test main.tests.TestClass    # single test class
python manage.py test main.tests.TestClass.test_method  # single test

# Migrations
python manage.py makemigrations
python manage.py migrate
```

## Architecture

### Django Project Layout

- **`jinjaGenerator/`** — Django project package (settings, root URL conf)
- **`main/`** — The single Django app containing all business logic
- **`main/renderer/`** — Core rendering engine (not a Django app, just a Python package)

### Rendering Pipeline

1. **Upload** (`POST /template/load`): Accepts a ZIP file, extracts it into `templates/<name>/`.
2. **Render** (`POST /template/render?template_name=<name>`): Takes JSON body as context, walks the template's `project/` folder, renders `.jinja`/`.j2` files through Jinja2, copies other files as-is. Output lands in `toutput/<name>/`.

### Template Package Structure

Each template under `templates/` follows this convention:

```
templates/<name>/
  project/        # REQUIRED — files to render/copy to output
  filters/        # Python files → loaded as Jinja2 filters (e.g. {{ value|myfilter }})
  tests/          # Python files → loaded as Jinja2 tests (e.g. {{ value is mytest }})
  fragments/      # Jinja2 partials, callable via render_fragment()
  macros/         # Jinja2 macros
  <other>/        # Any other folder → Python exports added to Jinja2 globals
```

Only `project/` is required. All other folders are optional and auto-discovered by `loader.py`.

### Rendering Capabilities

#### File handling

- Files ending in `.jinja` or `.j2` are rendered through Jinja2 and the extension is stripped from output (e.g., `t1.html.jinja` → `t1.html`).
- All other files are copied as-is to the output folder.

#### Wildcard path resolution (`%expression%`)

File and directory names in `project/` can contain `%expression%` wildcards that expand against the JSON context at render time. This is the core mechanism for generating multiple output files from a single template.

**Simple substitution** — scalar value from context:
```
# Filename:  t3%name%.py
# Context:   {"name": "john_doe"}
# Output:    t3john_doe.py
```

**Dot-notation traversal** — nested object access:
```
# Filename:  t4.%object.name%.%object.value%.html.j2
# Context:   {"object": {"name": "a", "value": 2}}
# Output:    t4.a.2.html
```

**List expansion** — generates one output per array item:
```
# Filename:  models/%models.name%.out.j2
# Context:   {"models": [{"name": "user"}, {"name": "post"}]}
# Output:    models/user.out  AND  models/post.out
```

**Filter chaining with `$`** — pipe the resolved value through filters/globals:
```
# Filename:  models/%models.name$uppercase%.txt.j2
# Output:    models/USER.txt  AND  models/POST.txt

# Filters can take arguments:
# Filename:  %models.name$truncate(3)%.txt.j2

# Multiple filters chain left-to-right:
# Filename:  %models.name$context_aware_filter('param1')$truncate(10)%.txt.j2
```

**Global function calls in paths** — call globals (from `other/`) to transform context before expansion:
```
# Filename:  controller%get_non_hidden_models().name%/%get_non_hidden_models().name$uppercase%.txt.j2
# get_non_hidden_models() filters the models list, then .name expands each result
```

**Wildcards in directory names** — create dynamic directory structures:
```
# Filename:  rootdir/service%models.name%/%models.name$uppercase%.txt.j2
# Output:    rootdir/serviceuser/USER.txt  AND  rootdir/servicepost/POST.txt
```

#### `_path` context variable

Inside rendered templates, `_path` is automatically set to a dict containing the resolved wildcard values for that file. Templates access it via `{{ _path | tojson }}` or `{{ _path["object.name"] }}`.

#### Custom filters (`filters/`)

Python files in `filters/` are dynamically imported. All non-underscore-prefixed callables become Jinja2 filters. Filters can be context-aware using `@pass_context`:

```python
from jinja2 import pass_context

@pass_context
def context_aware_filter(ctx, value, param1):
    return f"{value} (time: {ctx['current_time']})"

def uppercase(value):
    return value.upper()
```

#### Custom tests (`tests/`)

Same loading mechanism as filters. Callables become Jinja2 tests usable with `is`:

```python
def adult(age):
    return age >= 18
```
```jinja
{% if value2 is adult %} an adult {% endif %}
```

#### Globals (`other/` and any non-reserved folder)

Python exports from folders other than `project/`, `filters/`, `tests/`, `fragments/`, and `macros/` are added to Jinja2 globals. This includes both functions and constants:

```python
# other/constants.py
DATA = "abc"          # → {{ DATA }} in templates

# other/functions.py
@pass_context
def get_non_hidden_models(ctx):
    return [m for m in ctx['models'] if not m.get('hidden', False)]
```

#### Fragments (`fragments/`)

Jinja2 partials rendered via the built-in `render_fragment()` global. Fragments receive the parent context plus optional additional context:

```jinja
{{ render_fragment('simple.txt', {'a': 2}) }}
```

#### Macros (`macros/`)

Standard Jinja2 macros, imported in templates with `{% import 'macros/form' as macros %}`:

```jinja
{{ macros.render_input('[NAME]', label='[LABEL]') }}
```

### Key Renderer Modules

- **`renderer.py`** — Orchestrates rendering: creates output folder, walks `project/`, delegates to Jinja2 or copies static files.
- **`loader.py`** — Builds the Jinja2 `Environment`: auto-discovers and dynamically imports Python files from template subfolders to register filters, tests, and globals.
- **`wildcard_resolver.py`** — Resolves `%...%` wildcards in file paths, supporting dot-notation traversal, filter piping (`$`), list expansion, and recursive resolution of multiple wildcards in a single path.
- **`defaults.py`** — Provides `render_fragment`, a Jinja2 global that renders partials from `fragments/`.

## Conventions

- **`pysqlite3` shim**: `manage.py` patches `sys.modules['sqlite3']` with `pysqlite3` before Django loads. Maintain this if modifying the entry point.
- **CSRF is disabled** both via commented-out middleware and `@csrf_exempt` on views. All API endpoints accept raw POST requests.
- **No REST framework** — views are plain Django function views returning `JsonResponse`.
- **Template model** (`main/models.py`) only stores `name` and `folder` path; actual template content lives on the filesystem under `templates/`.
- Private functions in the renderer use the `__` prefix naming convention (e.g., `__create_output_folder`).

## Maintaining This File

The template package structure and rendering capabilities are actively evolving. When changes are made to the renderer modules or the template convention (e.g., new folder types, new wildcard syntax, new built-in globals), update the relevant sections above to keep them accurate.
