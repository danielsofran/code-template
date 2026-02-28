# Notes

## Macros vs Fragments

Both produce reusable chunks of template output, but they work differently:

**Fragments** (`fragments/`) are standalone Jinja2 template files rendered via the `render_fragment()` global. They receive a **full copy of the parent context** (plus optional extra variables) and render independently — essentially a sub-render call:

```jinja
{{ render_fragment('simple.txt', {'a': 2}) }}
```

**Macros** (`macros/`) are standard Jinja2 macros defined with `{% macro %}` inside a file. They're imported into a template and called like functions — they only see the **arguments you explicitly pass**, not the surrounding context:

```jinja
{% import 'macros/form' as macros %}
{{ macros.render_input('[NAME]', label='[LABEL]') }}
```

**In short**: fragments are context-aware sub-templates (they inherit the full render context), macros are isolated callable blocks (they only know their parameters).
