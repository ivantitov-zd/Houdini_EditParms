def markErrorInExpr(expr, exception):
    position = exception.offset - 1
    return '{}[{}]{}'.format(
        expr[:max(position, 0)],
        expr[position] if 0 <= position < len(expr) else '',
        expr[position + 1:]
    )
