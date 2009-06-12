from django import template

register = template.Library()

class WithblockNode(template.Node):
    def __init__(self, value_nodes, as_node, template_nodes):
        self.value_nodes    = value_nodes
        self.as_node        = as_node
        self.template_nodes = template_nodes

    def render(self, context):
        value = self.value_nodes.render(context)
        variable_name = self.as_node.variable_name
        context.push()
        context[variable_name] = value
        result = self.template_nodes.render(context)
        context.pop()
        return result

@register.tag
def withblock(parser, token):
    try:
        (tag_name,) = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag accepts no arguments" % token.contents.split()[0])

    nodes = parser.parse(('endwithblock',))
    parser.delete_first_token()

    value_nodes = template.NodeList()
    as_node = None
    while nodes:
        next_node = nodes.pop(0)
        if isinstance(next_node, AsNode):
            as_node = next_node
            break
        value_nodes.append(next_node)
    if as_node is None:
        raise template.TemplateSyntaxError("%r tag with no corresponding 'as' tag" % tag_name)

    return WithblockNode(value_nodes, as_node, nodes)

class AsNode(template.Node):
    def __init__(self, variable_name):
        self.variable_name = variable_name

    def render(self, context):
        raise template.TemplateSyntaxError("%r tag used outside 'withblock' tag" % (tag_name,))

@register.tag(name='as')
def do_as(parser, token):
    try:
        tag_name, variable_name = token.split_contents()
    except ValueError:
        tag_name = token.contents.split()[0]
        raise template.TemplateSyntaxError("%r tag requires one argument (variable name)" % (tag_name,))

    return AsNode(variable_name)
