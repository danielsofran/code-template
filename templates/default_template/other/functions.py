from jinja2 import pass_context


def multiply(x, y):
    return float(x) * float(y)

@pass_context
def content_aware_function(ctx, x, y): # can have **kwargs if needed
    return f"Result: {float(x) * float(y)} (Current time: {ctx['current_time']})"

@pass_context
def get_non_hidden_models(ctx):
    return [model for model in ctx['models'] if not model.get('hidden', False)]