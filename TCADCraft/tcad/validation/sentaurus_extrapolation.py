"""Verify a narrow paired deck intervention before attributing predictor effects.

The supported baseline has exactly one global Math Extrapolate(Order=2).
The comparison removes it; every other code token, including strings, must
remain identical. Comments and whitespace are ignored. This checks declared
input policy only. Solver logs, field identity and physical audits remain
independent requirements; no internal prediction formula is inferred.
"""
import re

_TOKEN = re.compile(r'[A-Za-z_][A-Za-z_0-9]*|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|[^\s]')
_DIRECTIVE = ['Extrapolate', '(', 'Order', '=', '2', ')']


def _tokens(text):
    if not isinstance(text, str):
        raise ValueError('deck must be text')
    result = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
        elif text.startswith('//', index):
            end = text.find('\n', index)
            index = len(text) if end < 0 else end + 1
        elif text.startswith('/*', index):
            end = text.find('*/', index + 2)
            if end < 0:
                raise ValueError('unterminated block comment')
            index = end + 2
        elif text[index] == '"':
            start = index
            index += 1
            while index < len(text):
                if text[index] == '\\':
                    index += 2
                elif text[index] == '"':
                    index += 1
                    result.append(text[start:index])
                    break
                else:
                    index += 1
            else:
                raise ValueError('unterminated quoted string')
        else:
            token = _TOKEN.match(text, index)
            if token is None:
                raise ValueError('unrecognized deck text')
            result.append(token.group())
            index = token.end()
    return result


def _structure(tokens):
    stack = []
    maths = []
    extrapolations = []
    for index, token in enumerate(tokens):
        if token == '{':
            name = tokens[index - 1] if index else None
            if name == 'Math':
                if stack:
                    raise ValueError('nested Math block is unsupported')
                maths.append(index)
            stack.append(name)
        elif token == '}':
            if not stack:
                raise ValueError('unmatched closing brace')
            stack.pop()
        elif token in ('Extrapolate', 'NoExtrapolate'):
            extrapolations.append((index, tuple(stack)))
    if stack:
        raise ValueError('unclosed deck brace')
    if len(maths) != 1:
        raise ValueError('exactly one global Math block is required')
    return extrapolations


def audit_extrapolation_deck_pair(baseline_deck, disabled_deck):
    """Check the declared order-2/removal intervention without running a solver.

    Unknown/local/repeated extrapolation directives, changes in other code,
    malformed comments, quoted strings or braces all fail closed. This is a
    policy audit for the stated deck subset, not a general Sentaurus parser.
    A valid pair still requires log confirmation that extrapolation is disabled.
    """
    result = dict(valid=False, baseline_declared_mode=None,
                  comparison_declared_mode=None, only_directive_removed=False,
                  solver_configuration_verified=False,
                  commercial_alignment_qualified=False, errors=[])
    try:
        baseline, disabled = map(_tokens, (baseline_deck, disabled_deck))
        original, changed = map(_structure, (baseline, disabled))
        if len(original) != 1:
            raise ValueError('baseline must contain exactly one extrapolation directive')
        index, scope = original[0]
        if scope != ('Math',) or baseline[index:index + len(_DIRECTIVE)] != _DIRECTIVE:
            raise ValueError('baseline requires global Math Extrapolate(Order=2)')
        if changed:
            raise ValueError('comparison must contain no extrapolation directives')
        remainder = baseline[:index] + baseline[index + len(_DIRECTIVE):]
        if remainder != disabled:
            raise ValueError('other deck code changed')
        result.update(valid=True, baseline_declared_mode='order2',
                      comparison_declared_mode='omitted', only_directive_removed=True)
    except ValueError as exc:
        result['errors'].append(str(exc))
    return result
