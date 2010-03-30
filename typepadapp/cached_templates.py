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

"""
This dynamically patches a bunch of code in the Django template system to cache
parsed templates instead of re-parsing them with each page load.

It works by replacing django.template.loader.get_template with a function that
stores parsed templates in-memory in a dictionary (keyed by template name). The
rest of the changes are necessary to make cached templates work with the block
and extends loader tags.

To enable cached templates, import this module and call setup() when your Django
app starts up. A good place to do this setup is in your project's settings.py.

"""

from django.template import loader, loader_tags, NodeList, Template, TemplateDoesNotExist, TemplateSyntaxError
from django.template.context import Context
from django.utils.safestring import mark_safe


def get_template(template_name):
    if template_name not in _template_cache:
        source, origin = find_template_source(template_name)
        _template_cache[template_name] = get_template_from_string(source, origin, template_name)
    return _template_cache[template_name]


def Template__render(self, context):
    context.parser_context.push()
    try:
        return self.nodelist.render(context)
    finally:
        context.parser_context.pop()


class ParserContext(object):
    """A stack container to store Template state."""
    def __init__(self, dict_=None):
        dict_ = dict_ or {}
        self.dicts = [dict_]

    def __repr__(self):
        return repr(self.dicts)
    
    def __iter__(self):
        for d in self.dicts:
            yield d

    def push(self):
        d = {}
        self.dicts = [d] + self.dicts
        return d

    def pop(self):
        if len(self.dicts) == 1:
            raise ContextPopException
        return self.dicts.pop(0)

    def __setitem__(self, key, value):
        "Set a variable in the current context"
        self.dicts[0][key] = value

    def __getitem__(self, key):
        "Get a variable's value from the current context"
        return self.dicts[0][key]

    def __delitem__(self, key):
        "Deletes a variable from the current context"
        del self.dicts[0][key]

    def has_key(self, key):
        return key in self.dicts[0]

    __contains__ = has_key

    def get(self, key, otherwise=None):
        d = self.dicts[0]
        if key in d:
            return d[key]
        return otherwise


def Context__init(self, dict_=None, autoescape=True, current_app=None):
    dict_ = dict_ or {}
    self.dicts = [dict_]
    self.autoescape = autoescape
    self.current_app = current_app
    self.parser_context = ParserContext()


class BlockContext(object):
    def __init__(self):
        # Dictionary of FIFO queues.
        self.blocks = {}

    def add_blocks(self, blocks):
        for name, block in blocks.iteritems():
            if name in self.blocks:
                self.blocks[name].insert(0, block)
            else:
                self.blocks[name] = [block]

    def pop(self, name):
        try:
            return self.blocks[name].pop()
        except (IndexError, KeyError):
            return None

    def push(self, name, block):
        self.blocks[name].append(block)

    def get_block(self, name):
        try:
            return self.blocks[name][-1]
        except (IndexError, KeyError):
            return None


def BlockNode__render(self, context):
    context.push()
    if not context.parser_context.has_key('block_context'):
        context['block'] = self
        result = self.nodelist.render(context)
    else:
        block_context = context.parser_context['block_context']
        push = block = block_context.pop(self.name)
        if block is None:
            block = self
        # Create new block so we can store context without thread-safety issues
        block = loader_tags.BlockNode(block.name, block.nodelist)
        block.context = context

        context['block'] = block
        result = block.nodelist.render(context)

        if push is not None:
            block_context.push(self.name, push)
    context.pop()
    return result

def BlockNode__super(self):
    if self.context.parser_context.has_key('block_context'):
        block_context = self.context.parser_context['block_context']
        if block_context.get_block(self.name) is not None:
            return mark_safe(self.render(self.context))
    return ''


class CompiledParent(object):
    def __get__(self, obj, cls):
        if obj.parent_name_expr:
            def compiled_parent(context):
                return obj.get_parent(context)
        else:
            def compiled_parent(context):
                if not '_compiled_parent' in obj.__dict__:
                    obj.__dict__['_compiled_parent'] = obj.get_parent(context)
                return obj.__dict__['_compiled_parent']
        return compiled_parent


def ExtendsNode__init(self, nodelist, parent_name, parent_name_expr, template_dirs=None):
    self.nodelist = nodelist
    self.parent_name, self.parent_name_expr = parent_name, parent_name_expr
    self.blocks = dict([(n.name, n) for n in nodelist.get_nodes_by_type(loader_tags.BlockNode)])

def ExtendsNode__get_parent(self, context):
    if self.parent_name_expr:
        self.parent_name = self.parent_name_expr.resolve(context)
    parent = self.parent_name
    if not parent:
        error_msg = "Invalid template name in 'extends' tag: %r." % parent
        if self.parent_name_expr:
            error_msg += " Got this from the '%s' variable." % self.parent_name_expr.token
        raise TemplateSyntaxError, error_msg
    if hasattr(parent, 'render'):
        return parent # parent is a Template object
    try:
        return loader.get_template(parent)
    except TemplateDoesNotExist:
        raise TemplateSyntaxError, "Template %r cannot be extended, because it doesn't exist" % parent

def ExtendsNode__render(self, context):
    compiled_parent = self.compiled_parent(context)

    if not context.parser_context.has_key('block_context'):
        context.parser_context['block_context'] = BlockContext()

    block_context = context.parser_context['block_context']

    # Add the block nodes from this node to the block context
    block_context.add_blocks(self.blocks)

    # If this block's parent doesn't have an extends node it is the root,
    # and its block nodes also need to be added to the block context.
    for node in compiled_parent.nodelist:
        # The ExtendsNode has to be the first non-text node.
        if not isinstance(node, loader_tags.TextNode):
            if not isinstance(node, loader_tags.ExtendsNode):
                blocks = dict([(n.name, n) for n in 
                               compiled_parent.nodelist.get_nodes_by_type(loader_tags.BlockNode)])
                block_context.add_blocks(blocks)
            break

    # Call render on nodelist explicitly so the block context stays
    # the same.
    return compiled_parent.nodelist.render(context)


def setup():
    "Monkeypunch!"
    loader.get_template.func_code = get_template.func_code
    loader.get_template.func_globals['_template_cache'] = {}
    Context.__init__ = Context__init
    Template.render = Template__render
    loader_tags.BlockNode.render = BlockNode__render
    loader_tags.BlockNode.super = BlockNode__super
    loader_tags.ExtendsNode.__init__ = ExtendsNode__init
    loader_tags.ExtendsNode.get_parent = ExtendsNode__get_parent
    loader_tags.ExtendsNode.render = ExtendsNode__render
    loader_tags.ExtendsNode.compiled_parent = CompiledParent()
