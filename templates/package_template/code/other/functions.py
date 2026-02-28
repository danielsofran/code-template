from jinja2 import pass_context


def multiply(x, y):
    return float(x) * float(y)

@pass_context
def content_aware_function(ctx, x, y): # can have **kwargs if needed
    return f"Result: {float(x) * float(y)} (Current time: {ctx['current_time']})"