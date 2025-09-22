import random
import re
import string
from typing import List, Tuple, Dict, Any, Callable

from jinja2 import Environment

def __deep_merge(dict1, dict2):
    """
    Deep merge two dictionaries.
    dict2 values will override dict1 values.
    For nested dicts, merge recursively.
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = __deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def __create_evaluation_context(context: dict, env: Environment) -> Dict[str, Any]:
    """
    Create a context suitable for evaluating wildcards.
    This includes callable items from the context and Jinja2 filters and tests.
    """
    eval_context = context.copy()
    # add jinja2 filters
    for filter_name, filter_func in env.filters.items():
        eval_context[filter_name] = filter_func
    # add jinja2 globals
    for global_name, global_value in env.globals.items():
        eval_context[global_name] = global_value
    return eval_context.copy()

def __extract_filters(wildcard: str, env: Environment,
    checker: Callable[[str, Environment], bool] = lambda x, env: x in env.filters) -> Tuple[str, List[Tuple[Callable, List[str]]]]:
    """
    Extract filter functions and their raw argument strings.
    :param checker: Function to check if a filter exists in the environment. Can be replaced with checking globals as well.
    :returns: tuple(base, List of tuples (filter_function, [raw_args]))
    """
    if '$' not in wildcard:
        return wildcard.strip(), []

    base_part, *filter_specs = wildcard.split('$')
    base_part = base_part.strip()

    filters = []
    for filter_spec in filter_specs:
        filter_spec = filter_spec.strip()

        # Filter without arguments
        if checker(filter_spec, env):
            filters.append((env.filters[filter_spec] if filter_spec in env.filters else env.globals[filter_spec], []))
        # Filter with arguments
        elif '(' in filter_spec and filter_spec.endswith(')'):
            fname, fargs = filter_spec.split('(', 1)
            fname = fname.strip()
            if not checker(fname, env):
                raise Exception(f"Filter '{filter_spec}' not found in Jinja2 environment.")

            # Extract raw arguments (still as strings)
            args_str = fargs[:-1]  # remove closing parenthesis
            raw_args = [arg.strip() for arg in args_str.split(',') if arg.strip()]
            filters.append((env.filters[fname] if fname in env.filters else env.globals[fname], raw_args))
        else:
            raise Exception(f"Filter '{filter_spec}' not found in Jinja2 environment.")

    return base_part, filters

def __evaluate_filter_args(raw_args: List[str], filter_name: str, eval_context: dict) -> List[Any]:
    """
    Evaluate raw argument strings to actual values.
    :param raw_args: List of raw argument strings
    :param filter_name: Name of the filter (for error messages)
    :param eval_context: Evaluation context
    :returns: List of evaluated arguments
    """
    evaluated_args = []
    for arg in raw_args:
        try:
            evaluated_arg = eval(arg, {}, eval_context)
            evaluated_args.append(evaluated_arg)
        except Exception as e:
            # Try treating the argument as a string literal
            try:
                evaluated_arg = eval(f"'{arg}'", {}, eval_context)
                evaluated_args.append(evaluated_arg)
            except Exception as e2:
                raise Exception(f"Error evaluating argument '{arg}' for filter '{filter_name}': {e}; {e2}")
    return evaluated_args

def __evaluate_expression(expression: str, eval_context: dict, env: Environment) -> Any:
    # try to evaluate as a filter
    _, values = __extract_filters("IGNORED_BASE$" + expression, env, lambda x, env: x in env.filters or x in env.globals)
    fname, fargs = values[0]
    fargs = __evaluate_filter_args(fargs, fname.__name__, eval_context)
    if getattr(fname, 'jinja_pass_arg', None) is not None:
        pass_arg = getattr(fname, 'jinja_pass_arg')
        if getattr(pass_arg, 'name', None) == 'context':
            fargs = [eval_context] + fargs
        elif getattr(pass_arg, 'name', None) == 'environment':
            fargs = [env] + fargs
    return fname(*fargs)

def __process_wildcard(wildcard: str, eval_context: dict, env: Environment, previous_resolved_value = None) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Process a wildcard and return the resolved string and additional context.
    Returns a list of tuples (resolved_path, additional_context)
    :example:
    wildcard = "models.user.fields"
    This will evaluate models from the context, then user from models, then fields from user.
    """
    parts = wildcard.split('.')
    part = parts[0]
    rest = '.'.join(parts[1:])

    # eval this part
    resolved_part = None
    exception = None
    try: resolved_part = eval(part, {}, eval_context)
    except Exception as e:
        # try to evaluate as filter / global functio
        try: resolved_part = __evaluate_expression(part, eval_context, env)
        except Exception: pass

    resolved_value = previous_resolved_value
    if resolved_value is None:
        if resolved_part is not None:
            resolved_value = resolved_part
        else:
            print(f"Error evaluating part '{part}' of wildcard '{wildcard}': {exception}")
            raise exception
    elif isinstance(resolved_value, dict):
        if part in resolved_value:
            resolved_value = resolved_value[part]
        elif resolved_part is not None and isinstance(resolved_part, str) and resolved_part in resolved_value:
            resolved_value = resolved_value[part]
        else:
            RESOLVED_VALUE = resolved_value
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            try: resolved_value = eval(f"RESOLVED_VALUE_{random_suffix}[{part}]", {f'RESOLVED_VALUE_{random_suffix}': RESOLVED_VALUE})
            except Exception as e:
                print(f"Error evaluating part '{part}' of wildcard '{wildcard}': {e}")
                raise e
    elif isinstance(resolved_value, list):
        new_resolved_values = []
        for item in resolved_value:
            new_resolved_values += __process_wildcard(wildcard, eval_context, env, item)
        resolved_value = new_resolved_values
    else:
        raise Exception(f"Error evaluating part '{part}': {resolved_value}")

    if len(parts) > 1:
        resolved_rest = __process_wildcard(rest, eval_context, env, resolved_value)
        # need to enhance. add {part}.{item.resolved_path} to the resolved_path
        # and same for the keys in the additional context
        return [
            # (item[0], {f"{part}.{k}": v for k, v in item[1].items()})
            (item[0], {part: item[1]})
            for item in resolved_rest
        ]
    if not isinstance(resolved_value, dict) and not isinstance(resolved_value, list):
        return [(str(resolved_value), {wildcard: str(resolved_value)})]
    elif isinstance(resolved_value, list):
        return resolved_value
    raise Exception(f"Error evaluating part '{part}': {resolved_value}. Unknown resolved_value type.")


def resolve_path(path: str, context: dict, env: Environment) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Resolve a path with possible wildcards using the context.
    Returns a list of tuples (resolved_path, additional_context)
    """
    if path.count('%') < 2:
        return [(path, {})]
    evaluation_context = __create_evaluation_context(context, env)
    start_index = path.find('%')
    end_index = path.find('%', start_index + 1)
    wildcard = path[start_index + 1:end_index]
    value, filters = __extract_filters(wildcard, env)
    resolved_paths = __process_wildcard(value, evaluation_context, env)
    rez = []
    for resolved_path, additional_context in resolved_paths:
        final_additional_context = __deep_merge(context, additional_context)
        for filter_func, raw_args in filters:
            eval_args = __evaluate_filter_args(raw_args, filter_func.__name__, __create_evaluation_context(final_additional_context, env))
            has_special_arg = False
            # if function is annotated with pass_context, add the context as first argument
            if getattr(filter_func, 'jinja_pass_arg', None) is not None:
                # what to pass: context or environment?
                pass_arg = getattr(filter_func, 'jinja_pass_arg')
                if getattr(pass_arg, 'name', None) == 'context':
                    eval_args = [final_additional_context] + eval_args
                    has_special_arg = True
                elif getattr(pass_arg, 'name', None) == 'environment':
                    eval_args = [env] + eval_args
                    has_special_arg = True
            if not callable(filter_func):
                raise Exception(f"Filter '{filter_func}' is not callable.")
            try:
                resolved_path = filter_func(eval_args[0], resolved_path, *eval_args[1:]) if has_special_arg \
                    else filter_func(resolved_path, *eval_args)
            except Exception as e:
                raise Exception(f"Error applying filter '{filter_func.__name__}' with args {eval_args} on value '{resolved_path}': {e}")
            # update the context with the new resolved_path
            resolved_path = re.sub(r'[^a-zA-Z0-9/._-]', '', str(resolved_path).replace('\\', '/'))
            additional_context[wildcard] = resolved_path
            final_additional_context[wildcard] = resolved_path

        new_path = path[:start_index] + resolved_path + path[end_index + 1:]
        start_rez_index = len(rez)
        rez += resolve_path(new_path, final_additional_context, env)
        for i in range(start_rez_index, len(rez)):
            rez[i][1].update(__deep_merge(rez[i][1], additional_context))
    return rez
