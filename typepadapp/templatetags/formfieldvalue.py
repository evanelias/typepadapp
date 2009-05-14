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
