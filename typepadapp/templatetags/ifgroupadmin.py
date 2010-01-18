# Copyright (c) 2009 Six Apart Ltd.
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


class IfGroupAdminNode(template.Node):
    def __init__(self, true_nodes, false_nodes, user_var):
        self.true_nodes = true_nodes
        self.false_nodes = false_nodes
        self.user_var = user_var

    def render(self, context):
        user = context.get(self.user_var)
        req = context.get('request')
        group = req.group
        if user.is_group_admin(group):
            return self.true_nodes.render(context)
        else:
            return self.false_nodes.render(context)

@register.tag
def ifgroupadmin(parser, token):
    try:
        tag_name, user = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires one argument (user variable)" % token.contents.split()[0])

    true_nodes = parser.parse(('else', 'endifgroupadmin'))
    token = parser.next_token()
    if token.contents == 'else':
        false_nodes = parser.parse(('endifgroupadmin',))
        parser.delete_first_token()
    else:
        false_nodes = template.NodeList()
    return IfGroupAdminNode(true_nodes, false_nodes, user)
