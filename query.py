import operator
import math
import waxeye
from parsers.parser import Parser as P


axes = {
    'ancestor'              : lambda context, field_filter: exception(field_filter),
    'ancestor-or-self'      : lambda context, field_filter: exception(field_filter),
    'attribute'             : lambda context, field_filter: axis_attribute(context, field_filter),
    'child'                 : lambda context, field_filter: axis_child(context, field_filter),
    'descendant'            : lambda context, field_filter: axis_descendant(context, field_filter),
    'descendant-or-self'    : lambda context, field_filter: axis_descendant_or_self(context, field_filter),
    'following'             : lambda context, field_filter: exception(field_filter),
    'following-sibling'     : lambda context, field_filter: exception(field_filter),
    'namespace'             : lambda context, field_filter: exception(field_filter),
    'parent'                : lambda context, field_filter: axis_parent(context, field_filter),
    'preceding'             : lambda context, field_filter: exception(field_filter),
    'preceding-sibling'     : lambda context, field_filter: exception(field_filter),
    'self'                  : lambda context, field_filter: axis_self(context, field_filter),
    '@'                     : lambda context, field_filter: axis_attribute(context, field_filter)
}


matchers = {
    'path'                  : lambda node, context: match_path(node, context),
    'node_test'             : lambda node, context: match_node_test(node, context),
    'predicate'             : lambda node, context: eval_predicate(node, context),
    'predicate_expr'        : lambda node, context: matchers[node.children[0].type](node.children[0], context),
    'or_expr'               : lambda node, context: match_or_expr(node, context),
    'and_expr'              : lambda node, context: match_and_expr(node, context),
    'equality_expr'         : lambda node, context: eval_bin_op(node, context),
    'relational_expr'       : lambda node, context: eval_bin_op(node, context),
    'additive_expr'         : lambda node, context: eval_bin_op(node, context),
    'multiplicative_expr'   : lambda node, context: eval_bin_op(node, context),
    'primary_expr'          : lambda node, context: match_primary_expr(node, context),
    'unary_expr'            : lambda node, context: match_unary_expr(node, context),
    'argument'              : lambda node, context: eval_unary_expr(node.children[0], context)
}


functions = {
    'last'                  : lambda context, *args: context['size'],
    'position'              : lambda context, *args: context['pos'],
    'count'                 : lambda context, *args: len(args[0]),
    'not'                   : lambda context, *args: not bool(args[0]),
    'true'                  : lambda context, *args: True,
    'false'                 : lambda context, *args: False,
    'lang'                  : lambda context, *args: False,
    'string-length'         : lambda context, *args: len(args[0]),
    'concat'                : lambda context, *args: ''.join(args),
    'contains'              : lambda context, *args: args[0] in args[1],
    'substring-before'      : lambda context, *args: substring_before(context, *args),
    'substring-after'       : lambda context, *args: substring_after(context, *args),
    'sum'                   : lambda context, *args: sum((float(x['value']) for x in args[0])),
    'floor'                 : lambda context, *args: math.floor(args[0]),
    'ceiling'               : lambda context, *args: math.ceil(args[0]),
    'round'                 : lambda context, *args: round(args[0]),
}


operators = {
    '+'         : operator.add,
    '-'         : operator.sub,
    '*'         : operator.mul,
    'd'         : operator.div,
    'm'         : operator.mod,
    '='         : operator.eq,
    '!='        : operator.ne,
    '>'         : operator.gt,
    '<'         : operator.lt,
    '>='        : operator.ge,
    '<='        : operator.le
}


class InvalidQueryException(Exception):
    pass


def exception(ast):
    raise InvalidQueryException(str(ast))


##
## Axes
##

def axis_child(context, field_filter):
    field_set = []
    fields = context['value'].ListFields()

    for f_meta, f_value in fields:
        if f_meta.type == f_meta.TYPE_MESSAGE:
            if match_node_test(field_filter, dict(meta=f_meta, value=f_value, pos=0, size=0)):
                if f_meta.label == f_meta.LABEL_REPEATED:
                    map(lambda f: field_set.append(dict(meta=f_meta, value=f, pos=0, size=0)), f_value)
                else:
                    field_set.append(dict(meta=f_meta, value=f_value, pos=0, size=0))

    return field_set


def axis_parent(context, field_filter):
    field_set = []

    if hasattr(context['value']._listener, '_parent_message_weakref'):
        parent = context['value']._listener._parent_message_weakref
        meta = parent.DESCRIPTOR.file
        field_set.append(dict(meta=meta, value=parent, pos=1, size=1))

    return field_set


def get_children(context):
    field_set = []
    fields = context['value'].ListFields()

    for f_meta, f_value in fields:
        #print f_meta.name
        if f_meta.type == f_meta.TYPE_MESSAGE:
            if f_meta.label == f_meta.LABEL_REPEATED:
                for f in f_value:
                    field_set.append(dict(meta=f_meta, value=f, pos=0, size=0))
            else:
                field_set.append(dict(meta=f_meta, value=f_value, pos=0, size=0))

    return field_set


def axis_descendant(context, field_filter):
    result = []
    walking_set = get_children(context)

    for f in walking_set:
        if match_node_test(field_filter, f):
            result.append(f)

    for f in walking_set:
        result.extend(axis_descendant(f, field_filter))

    return result


def axis_descendant_or_self(context, field_filter):
    result = []

    if match_node_test(field_filter, context):
        result.append(context)

    result.extend(axis_descendant(context, field_filter))

    return result


def axis_self(context, field_filter):
    result = []

    if match_node_test(field_filter, context):
        result.append(context)

    return result


def axis_attribute(context, field_filter):
#    if context['meta'].type != context['meta'].TYPE_MESSAGE:
#        return []

    field_set = []
    fields = context['value'].ListFields()

    for f_meta, f_value in fields:
        if f_meta.type != f_meta.TYPE_MESSAGE:
            if match_node_test(field_filter, dict(meta=f_meta, value=f_value, pos=0, size=0)):
                if f_meta.label == f_meta.LABEL_REPEATED:
                    for f in f_value:
                        field_set.append(dict(meta=f_meta, value=f, pos=0, size=0))
                else:
                    field_set.append(dict(meta=f_meta, value=f_value, pos=0, size=0))

    return field_set


##
## 
##


def substring_after(context, *args):
    try:
        return args[0][args[0].index(args[1])+len(args[1]):]
    except ValueError:
        return ''


def substring_before(context, *args):
    try:
        return args[0][0:args[0].index(args[1])]
    except ValueError:
        return ''


def string_length(node, context):
    arg = node.children[1]
    result = eval_unary_expr(arg.children[0], context)
    return len(result)


def function_call(node, context):
    function_name = get_string(node.children[0])

    args = []

    for c in node.children[1:]:
        a = matchers[c.type](c, context)
        args.append(a)

    print ">>>>>>>>", functions[function_name](context, *args)
    return functions[function_name](context, *args)


def eval_predicate(node, context):
    result = matchers[node.children[0].type](node.children[0], context)

    #print "predicate", result.__class__, result

    if isinstance(result, bool):
        return result
    elif isinstance(result, float) or isinstance(result, long):
        return context['pos'] == result
    else:
        return bool(result)


def match_unary_expr(node, context):
    result = 0
    if node.children[0] == '-':
        result = -(eval_unary_expr(node.children[1], context))
    else:
        result = eval_unary_expr(node.children[0], context)

    return result


def eval_unary_expr(node, context):
    matched = matchers[node.type](node, context)
    if isinstance(matched, list):
        if len(matched) == 1:
            matched = matched[0]
#        else:
#            matched = None

    if isinstance(matched, dict):
        if matched['meta'].type == matched['meta'].TYPE_MESSAGE:
            exception(node)
        return matched['value']
    else:
        return matched


def eval_bin_op(node, context):
    state = 0
    lvalue = 0

    for c in node.children:
        if state == 0:
            lvalue = eval_unary_expr(c, context)
            state = 1
        elif state == 1:
            op = get_string(c)
            state = 2
        elif state == 2:
            rvalue = eval_unary_expr(c, context)
            state = 1
            lvalue = operators[op](lvalue, rvalue)

    print "result", lvalue
    return lvalue


def match_primary_expr(node, context):
    child = node.children[0]

    if child.type == 'number':
        return get_number(child)
    elif child.type == 'literal':
        return get_string(child)
    elif child.type == 'function_call':
        return function_call(child, context)
    else:
        return matchers[child.type](child, context)


def match_or_expr(node, context):
    for c in node.children:
        if matchers[c.type](c, context):
            return True
    return False


def match_and_expr(node, context):
    for c in node.children:
        if matchers[c.type](c, context) == False:
            return False
    return True


def match_location_step(context, axis_specifier, node_test):
    if axis_specifier == None or len(axis_specifier.children) == 0:
        axis = 'child'
    else:
        axis = get_string(axis_specifier.children[0])

    field_set = axes[axis](context, node_test)

    return field_set


def match_step(node, context):
    axis_specifier = None
    node_test = None
    predicates = []
    abbreviated_step = None

    for c in node.children:
        if c.type == 'axis_specifier':
            axis_specifier = c
        elif c.type == 'node_test':
            node_test = c
        elif c.type == 'predicate':
            predicates.append(c)
        elif c.type == 'abbreviated_step':
            abbreviated_step = get_string(c)

    context_set = []
    if abbreviated_step == None:
        context_set = match_location_step(context, axis_specifier, node_test)
    elif abbreviated_step == '.':
        context_set.append(context)
    elif abbreviated_step == '..':
        context_set.extend(axis_parent(context, None))

    def update_order(context_set):
        for i, c in enumerate(context_set):
            c['pos'] = i + 1
            c['size'] = len(context_set)

    for p in predicates:
        update_order(context_set)
        context_set = filter(lambda c: matchers['predicate'](p, c), context_set)

    return context_set


def match_step_anywhere(node, context):
    if context['meta'].type != context['meta'].TYPE_MESSAGE:
        return []

    field_set = []

    # self
    field_set.extend(match_step(node, context))

    fields = context['value'].ListFields()

    for f_meta, f_value in fields:
        if f_meta.type == f_meta.TYPE_MESSAGE:
            if f_meta.label == f_meta.LABEL_REPEATED:
                for f in f_value:
                    field_set.extend(match_step_anywhere(node, dict(meta=f_meta, value=f, pos=0, size=0)))
            else:
                field_set.extend(match_step_anywhere(node, dict(meta=f_meta, value=f_value, pos=0, size=0)))

    return field_set


def match_node_test(node, context):
    lookup_field = get_string(node.children[0])

    if lookup_field == '*':
        return True
    elif node.children[0].type == 'node_type' and lookup_field == 'node':
        return context['meta'].type == context['meta'].TYPE_MESSAGE
    else:
        return get_string(node.children[0]) == context['meta'].name


def get_string(ast_node):
    if isinstance(ast_node, str):
        return ast_node
    else:
        return ''.join(ast_node.children)


def get_number(ast_node):
    return float(get_string(ast_node))


def get_integer(ast_node):
    return int(get_string(ast_node))


def match_path(ast_node, context):
    node_set = [context]
    anywhere = False

    for c in ast_node.children:
        if c == '/':
            anywhere = True
        elif c.type == 'step':
            result = []
            for f in node_set:
                if anywhere:
                    result.extend(match_step_anywhere(c, f))
                else:
                    result.extend(match_step(c, f))

            anywhere = False
            node_set = result

    return node_set


def process(ast_node, context):
    node_set = []

    for c in ast_node.children:
        node_set.extend(match_path(c, context))

    return node_set


def query(msg, path):
    ast = P().parse(path)
    if isinstance(ast, waxeye.ParseError):
        raise InvalidQueryException(str(ast))
    else:
        msg.DESCRIPTOR.TYPE_MESSAGE = 11
        msg.DESCRIPTOR.LABEL_REQUIRED = 2
        msg.DESCRIPTOR.type = msg.DESCRIPTOR.TYPE_MESSAGE
        msg.DESCRIPTOR.label = msg.DESCRIPTOR.LABEL_REQUIRED

        result = process(ast, dict(meta=msg.DESCRIPTOR, value=msg, pos=1, size=1))

        return [p['value'] for p in result]
