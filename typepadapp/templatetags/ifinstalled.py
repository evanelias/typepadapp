from django import template
from django.conf import settings

register = template.Library()


class IfinstalledEmptyNode(template.Node):
    def render(self, context):
        return ''


class IfinstalledNode(template.Node):
    def __init__(self, template_nodes):
        self.template_nodes = template_nodes

    def render(self, context):
        return self.template_nodes.render(context)


@register.tag
def ifinstalled(parser, token):
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError("%r tag requires 1 argument" % token.contents.split()[0])

    if bits[1] in settings.INSTALLED_APPS:
        nodes = parser.parse(('endifinstalled',))
        parser.delete_first_token()
        return IfinstalledNode(nodes)
    else:
        parser.skip_past('endifinstalled')
        return IfinstalledEmptyNode()
