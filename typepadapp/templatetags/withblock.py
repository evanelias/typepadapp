# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
