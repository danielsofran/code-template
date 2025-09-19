from jinja2 import pass_context, pass_environment, Environment, FileSystemLoader
from jinja2.runtime import Context


@pass_context
def render_fragment(ctx: Context, path, additional_context=None, overrides_context=False):
    if additional_context is None:
        additional_context = {}
    template = ctx.environment.get_template('fragments/' + path)
    full_context = {} if overrides_context else additional_context
    full_context.update(ctx.parent)
    return template.render(full_context)