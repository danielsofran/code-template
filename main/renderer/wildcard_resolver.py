from typing import List, Tuple, Dict, Any

from jinja2 import Environment


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

def __process_wildcard(wildcard: str, eval_context: dict, previous_resolved_value = None) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Process a wildcard and return the resolved string and additional context.
    Returns a list of tuples (resolved_path, additional_context)
    :example:
    wildcard = "models.user.fields"
    This will evaluate models from the context, then user from models, then fields from user.

    """
    parts = wildcard.split('.')
    resolved_value = None
    for part in parts:
        # eval this part
        resolved_part = None
        exception = None
        try: resolved_part = eval(part, {}, eval_context)
        except Exception as e: exception = e

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
                try: resolved_value = eval(f"RESOLVED_VALUE[{part}]", {'RESOLVED_VALUE': RESOLVED_VALUE})
                except Exception as e:
                    print(f"Error evaluating part '{part}' of wildcard '{wildcard}': {e}")
                    raise e
        elif isinstance(resolved_value, list):
            pass # TODO: call recursively for each item in the list
        else:
            raise Exception(f"Error evaluating part '{part}': {resolved_value}")
    return [(str(resolved_value), {wildcard: str(resolved_value)})]


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
    resolved_paths = __process_wildcard(wildcard, evaluation_context)
    rez = []
    for resolved_path, additional_context in resolved_paths:
        final_additional_context = context.copy()
        final_additional_context.update(additional_context)
        new_path = path[:start_index] + resolved_path + path[end_index + 1:]
        rez += resolve_path(new_path, final_additional_context, env)
        for i, _ in enumerate(rez):
            rez[i][1].update(additional_context)
    return rez
