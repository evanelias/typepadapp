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

def value_of_field(field):
    """Returns the value of the given field, as discerned for the form field's
    widget. That is:

    * if the field is bound, use the bound value
    * if the form has an initial value for the field, use that
    * if the field itself has an initial value, use that

    This is discovered as implemented in the uncommitted patch in Django
    ticket #10427:

    http://code.djangoproject.com/attachment/ticket/10427/django-forms-value.7.diff

    """
    if not field.form.is_bound:
        val = field.form.initial.get(field.name, field.field.initial)
        if callable(val):
            val = val()
    else:
        val = field.data
    if val is None:
        val = ''
    return val    

class FormFieldValueNode(template.Node):
    """Node for rendering the `formfieldvalue` tag.

    This node renders as the value of the specified form field, as discerned
    for the form field's widget. That is:

    * if the field is bound, use the bound value
    * if the form has an initial value for the field, use that
    * if the field itself has an initial value, use that

    """
    def __init__(self, fieldname):
        self.fieldname = fieldname

    def render(self, context):
        """Returns the value of the field represented by this node."""
        field = context.get(self.fieldname)
        return value_of_field(field)

@register.tag
def formfieldvalue(parser, token):
    """Renders the value of the specified form field.

    This tag takes one argument: the name of the template variable containing
    the field for which to render a value.

    """
    try:
        tag_name, fieldname = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires one argument (variable name)" % token.contents.split()[0])

    return FormFieldValueNode(fieldname)
