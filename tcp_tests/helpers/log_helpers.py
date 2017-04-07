import six


def _simple(item):
    """Check for nested iterations: True, if not"""
    return not isinstance(item, (list, set, tuple, dict))


_formatters = {
    'simple': "{spc:<{indent}}{val!r}".format,
    'text': "{spc:<{indent}}{prefix}'''{string}'''".format,
    'dict': "\n{spc:<{indent}}{key!r:{size}}: {val},".format,
}


def pretty_repr(src, indent=0, no_indent_start=False, max_indent=20):
    """Make human readable repr of object
    :param src: object to process
    :type src: object
    :param indent: start indentation, all next levels is +4
    :type indent: int
    :param no_indent_start: do not indent open bracket and simple parameters
    :type no_indent_start: bool
    :param max_indent: maximal indent before classic repr() call
    :type max_indent: int
    :return: formatted string
    """
    if _simple(src) or indent >= max_indent:
        indent = 0 if no_indent_start else indent
        if isinstance(src, (six.binary_type, six.text_type)):
            if isinstance(src, six.binary_type):
                string = src.decode(
                    encoding='utf-8',
                    errors='backslashreplace'
                )
                prefix = 'b'
            else:
                string = src
                prefix = 'u'
            return _formatters['text'](
                spc='',
                indent=indent,
                prefix=prefix,
                string=string
            )
        return _formatters['simple'](
            spc='',
            indent=indent,
            val=src
        )
    if isinstance(src, dict):
        prefix, suffix = '{', '}'
        result = ''
        max_len = len(max([repr(key) for key in src])) if src else 0
        for key, val in src.items():
            result += _formatters['dict'](
                spc='',
                indent=indent + 4,
                size=max_len,
                key=key,
                val=pretty_repr(val, indent + 8, no_indent_start=True)
            )
        return (
            '\n{start:>{indent}}'.format(
                start=prefix,
                indent=indent + 1
            ) +
            result +
            '\n{end:>{indent}}'.format(end=suffix, indent=indent + 1)
        )
    if isinstance(src, list):
        prefix, suffix = '[', ']'
    elif isinstance(src, tuple):
        prefix, suffix = '(', ')'
    else:
        prefix, suffix = '{', '}'
    result = ''
    for elem in src:
        if _simple(elem):
            result += '\n'
        result += pretty_repr(elem, indent + 4) + ','
    return (
        '\n{start:>{indent}}'.format(
            start=prefix,
            indent=indent + 1) +
        result +
        '\n{end:>{indent}}'.format(end=suffix, indent=indent + 1)
    )
