from jinja2 import pass_context

@pass_context
def context_aware_filter(ctx, value, param1): # can have **kwargs if needed
    return f"[VALUE]: {value} [PARAM1]: {param1} (Current time: {ctx['current_time']})"

def reverse(s):
    return s[::-1]

def capitalize(s):
    return ' '.join(word.capitalize() for word in s.split())

def replace(value, pattern='hello', replacement='HELLO'):
    return value.replace(pattern, replacement)

def truncate(value, length=100):
    if len(value) <= length:
        return value
    return value[:length] + '...'

def uppercase(value):
    return value.upper()
