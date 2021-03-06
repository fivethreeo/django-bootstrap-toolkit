import re

from math import floor

from django.forms import BaseForm
from django.forms.forms import BoundField
from django.forms.widgets import (TextInput, Textarea, CheckboxInput, Select, 
    SelectMultiple, CheckboxSelectMultiple, RadioSelect)
from django.template import Context
from django.template.loader import get_template
from django import template
from django.template import Library, Node, TemplateSyntaxError
from django.conf import settings

from django.utils.safestring import mark_safe
from django.utils.html import escape
from classytags.core import Options
from classytags.arguments import Argument, MultiKeywordArgument
from classytags.helpers import InclusionTag
from django.template.loader import render_to_string

register = template.Library()

BOOTSTRAP_BASE_URL = getattr(settings, 'BOOTSTRAP_BASE_URL',
                             '//netdna.bootstrapcdn.com/bootstrap/3.0.0-rc1/'
)

BOOTSTRAP_JS_BASE_URL = getattr(settings, 'BOOTSTRAP_JS_BASE_URL',
                                BOOTSTRAP_BASE_URL + 'js/'
)

BOOTSTRAP_JS_URL = getattr(settings, 'BOOTSTRAP_JS_URL',
                           BOOTSTRAP_JS_BASE_URL + "bootstrap.js"
)

BOOTSTRAP_CSS_BASE_URL = getattr(settings, 'BOOTSTRAP_CSS_BASE_URL',
                                 BOOTSTRAP_BASE_URL + 'css/'
)

BOOTSTRAP_CSS_URL = getattr(settings, 'BOOTSTRAP_CSS_URL',
                            BOOTSTRAP_CSS_BASE_URL + 'bootstrap.css'
)

register = template.Library()


def parse_args_kwargs_and_as_var(parser, bits):
    """
    Parse args, kwargs and the 'as' var. 
    """
    args = []
    kwargs = {}
    as_var = None
    
    bits = iter(bits)
    for bit in bits:
        if bit == 'as':
            as_var = bits.next()
            break
        else:
            for arg in bit.split(","):
                if '=' in arg:
                    k, v = arg.split('=', 1)
                    k = k.strip()
                    kwargs[k] = parser.compile_filter(v)
                elif arg:
                    args.append(parser.compile_filter(arg))
    return args, kwargs, as_var


@register.simple_tag
def bootstrap_stylesheet_url(css=None):
    """
    URL to Bootstrap Stylesheet (CSS)
    """
    if css:
        return BOOTSTRAP_CSS_BASE_URL + u'bootstrap-%s.css' % css
    else:
        return BOOTSTRAP_CSS_URL


@register.simple_tag
def bootstrap_stylesheet_tag(css=None):
    """
    HTML tag to insert Bootstrap stylesheet
    """
    return u'<link rel="stylesheet" href="%s">' % bootstrap_stylesheet_url(css)


@register.simple_tag
def glyphicons_stylesheet_url():
    """
    URL to Glyphicons Stylesheet (CSS)
    """
    return settings.STATIC_URL + "glyphicons/css/bootstrap-glyphicons.css"


@register.simple_tag
def glyphicons_stylesheet_tag():
    """
    HTML tag to insert Glyphicons stylesheet
    """
    return u'<link rel="stylesheet" href="%s">' % glyphicons_stylesheet_url()


@register.simple_tag
def bootstrap_javascript_url(name=None):
    """
    URL to Bootstrap javascript file
    """
    if name:
        return BOOTSTRAP_JS_BASE_URL + 'bootstrap-' + name + '.js'
    else:
        return BOOTSTRAP_JS_URL


@register.simple_tag
def bootstrap_javascript_tag(name=None):
    """
    HTML tag to insert bootstrap_toolkit javascript file
    """
    url = bootstrap_javascript_url(name)
    if url:
        return u'<script src="%s"></script>' % url
    return u''


@register.filter
def as_bootstrap(form_or_field, layout='vertical,false'):
    """
    Render a field or a form according to Bootstrap guidelines
    """
    params = split(layout, ",")
    layout = str(params[0]).lower()

    try:
        bootstrap_float = str(params[1]).lower() == "float"
    except IndexError:
        bootstrap_float = False

    if isinstance(form_or_field, BaseForm):
        return get_template("bootstrap_toolkit/form.html").render(
            Context({
                'form': form_or_field,
                'layout': layout,
                'float': bootstrap_float,
            })
        )
    elif isinstance(form_or_field, BoundField):
        return get_template("bootstrap_toolkit/field.html").render(
            Context({
                'field': form_or_field,
                'layout': layout,
                'float': bootstrap_float,
            })
        )
    else:
        # Display the default
        return settings.TEMPLATE_STRING_IF_INVALID


@register.filter
def is_disabled(field):
    """
    Returns True if fields is disabled, readonly or not marked as editable, False otherwise
    """
    if not getattr(field.field, 'editable', True):
        return True
    if getattr(field.field.widget.attrs, 'readonly', False):
        return True
    if getattr(field.field.widget.attrs, 'disabled', False):
        return True
    return False


@register.filter
def is_enabled(field):
    """
    Shortcut to return the logical negative of is_disabled
    """
    return not is_disabled(field)


@register.filter
def bootstrap_input_type(field):
    """
    Return input type to use for field
    """
    try:
        widget = field.field.widget
    except:
        raise ValueError("Expected a Field, got a %s" % type(field))
    input_type = getattr(widget, 'bootstrap_input_type', None)
    if input_type:
        return unicode(input_type)
    if isinstance(widget, TextInput):
        return u'text'
    if isinstance(widget, CheckboxInput):
        return u'checkbox'
    if isinstance(widget, CheckboxSelectMultiple):
        return u'checkbox'
    if isinstance(widget, RadioSelect):
        return u'radio'
    if isinstance(widget, Select):
        return u'select'
    if isinstance(widget, SelectMultiple):
        return u'select'
    if isinstance(widget, Textarea):
        return u'textarea'
    return u'default'


@register.filter
def bootstrap_prepend(field):
    if hasattr(field.field.widget, 'bootstrap'):
        return field.field.widget.bootstrap.get('prepend')
    return None


@register.filter
def bootstrap_append(field):
    if hasattr(field.field.widget, 'bootstrap'):
        return field.field.widget.bootstrap.get('append')
    return None


@register.simple_tag
def active_url(request, url, output=u'active'):
    # Tag that outputs text if the given url is active for the request
    if url == request.path:
        return output
    return ''


@register.filter
def pagination(page, pages_to_show=11):
    """
    Generate Bootstrap pagination links from a page object
    """
    context = get_pagination_context(page, pages_to_show)
    return get_template("bootstrap_toolkit/pagination.html").render(Context(context))


@register.filter
def split(text, splitter):
    """
    Split a string
    """
    return text.split(splitter)


@register.filter
def html_attrs(attrs):
    """
    Display the attributes given as html attributes :
    >>> import collections
    >>> html_attrs(collections.OrderedDict([('href',"http://theurl.com/img.png"), ('alt','hi "guy')]))
    u'href="http://theurl.com/img.png" alt="hi &quot;guy" '
    """
    pairs = []
    for name, value in attrs.items():
        pairs.append(u'%s="%s"' % (escape(name), escape(value)))
    return mark_safe(u' '.join(pairs))


class HTMLAttrs(Node):
    def __init__(self, args, kwargs, as_var):
        self.args = args
        self.kwargs = kwargs
        self.as_var = as_var
    
    def render(self, context):
        args = [a.resolve(context) for a in self.args]
        kwargs = dict([(k, v.resolve(context)) for k, v in self.kwargs.items()])
        attrs = self.get_attrs(args, kwargs)
        result = self.join_attrs(attrs)
        
        if self.as_var:
            context[self.as_var] = mark_safe(result)
            return ''
        else:
            return mark_safe(result)
    
    def get_attrs(self, args, kwargs):
        attrs = args[0] if len(args) else dict()
        for key, value in kwargs.items():
            try:
                attrs[key] += ' ' + value
            except KeyError:
                attrs[key] = value
        return attrs
    
    def join_attrs(self, attrs):
        pairs = []
        for name, value in attrs.items():
            pairs.append(u'%s="%s"' % (escape(name), escape(value)))
        return u' '.join(pairs)


@register.tag('html_attrs')
def html_attrs_tag(parser, token):
    """
    Like the `html_attrs` filter, this tag displays the passed dict of attrs 
    appropriate for inclusion in an HTML tag. It also allows additional keyed 
    arguments to be appended to the attrs.
    
    {% html_attrs attr_dict %} # Same functionality as `html_attrs`.
    
    {% html_attrs attr_dict class="foo" src="bar" %}
    
    {% html_attrs attr_dict class="foo" as html_attrs %}
    """
    bits = token.contents.split(' ')
    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least two arguments" % bits[0])
    
    if len(bits) > 2:
        args, kwargs, as_var = parse_args_kwargs_and_as_var(parser, bits[1:])
    else:
        args, kwargs, as_var = (bits[1], None, None)
    
    return HTMLAttrs(args, kwargs, as_var)


@register.simple_tag(takes_context=True)
def bootstrap_messages(context, *args, **kwargs):
    """
    Show request messages in Bootstrap style
    """
    return get_template("bootstrap_toolkit/messages.html").render(context)

class PushPopInclusionTag(InclusionTag):
    
    def render_tag(self, context, **kwargs):
        """
        INTERNAL!

        Gets the context and data to render.
        """
        template = self.get_template(context, **kwargs)
        context.push()
        data = self.get_context(context, **kwargs)
        output = render_to_string(template, data)
        context.pop()
        return output
        
class BootstrapForm(PushPopInclusionTag):
    name = 'bootstrap_form'
    template = 'bootstrap_toolkit/form.html'
    options = Options(
        Argument('form'),
        MultiKeywordArgument('kwargs')
    )
    def get_context(self, context, form, kwargs):
        context.update(kwargs)
        context['form'] = form
        return context

register.tag(BootstrapForm)

class BootstrapFormset(PushPopInclusionTag):
    name = 'bootstrap_formset'
    template = 'bootstrap_toolkit/formset.html'
    options = Options(
        Argument('formset'),
        MultiKeywordArgument('kwargs')
    )
    def get_context(self, context, formsset, kwargs):
        context.update(kwargs)
        context['formset'] = formset
        return context

register.tag(BootstrapFormset)

class BootstrapField(PushPopInclusionTag):
    name = 'bootstrap_field'
    template = 'bootstrap_toolkit/field.html'
    options = Options(
        Argument('field'),
        MultiKeywordArgument('kwargs')
    )
    def get_context(self, context, field, kwargs):
        context.update(kwargs)
        context['field'] = field
        return context

register.tag(BootstrapField)


@register.inclusion_tag("bootstrap_toolkit/button.html")
def bootstrap_button(text, **kwargs):
    """
    Render a button
    """
    button_type = kwargs.get('type', '')
    button_size = kwargs.get('size', '')
    button_disabled = kwargs.get('disabled', False) and kwargs.get('enabled', True)
    button_icon = kwargs.get('icon', '')

    # Build button classes
    button_class = 'btn'
    if button_type:
        button_class += ' btn-' + button_type
    else:
        button_class += ' btn-default'
    if button_size:
        button_class += ' btn-' + button_size
    if button_disabled:
        button_class += ' disabled'
        # Build icon classes
    icon_class = ''
    if button_icon:
        icon_class = 'glyphicon glyphicon-' + button_icon
        if button_type and button_type != 'link':
            icon_class += ' glyphicon-white'
            # Return context for template
    return {
        'text': text,
        'url': kwargs.get('url', '#'),
        'button_class': button_class,
        'icon_class': icon_class,
    }


@register.inclusion_tag("bootstrap_toolkit/icon.html")
def bootstrap_icon(icon, **kwargs):
    """
    Render an icon
    """
    icon_class = 'glyphicon glyphicon-' + icon
    if kwargs.get('inverse'):
        icon_class += ' glphyicon-white'
    return {
        'icon_class': icon_class,
    }


@register.inclusion_tag("bootstrap_toolkit/pagination.html")
def bootstrap_pagination(page, **kwargs):
    """
    Render pagination for a page
    """
    pagination_kwargs = kwargs.copy()
    pagination_kwargs['page'] = page
    return get_pagination_context(**pagination_kwargs)


def get_pagination_context(page, pages_to_show=11, url=None, size=None, align=None, extra=None):
    """
    Generate Bootstrap pagination context from a page object
    """
    pages_to_show = int(pages_to_show)
    if pages_to_show < 1:
        raise ValueError("Pagination pages_to_show should be a positive integer, you specified %s" % pages_to_show)
    num_pages = page.paginator.num_pages
    current_page = page.number
    half_page_num = int(floor(pages_to_show / 2)) - 1
    if half_page_num < 0:
        half_page_num = 0
    first_page = current_page - half_page_num
    if first_page <= 1:
        first_page = 1
    if first_page > 1:
        pages_back = first_page - half_page_num
        if pages_back < 1:
            pages_back = 1
    else:
        pages_back = None
    last_page = first_page + pages_to_show - 1
    if pages_back is None:
        last_page += 1
    if last_page > num_pages:
        last_page = num_pages
    if last_page < num_pages:
        pages_forward = last_page + half_page_num
        if pages_forward > num_pages:
            pages_forward = num_pages
    else:
        pages_forward = None
        if first_page > 1:
            first_page -= 1
        if pages_back > 1:
            pages_back -= 1
        else:
            pages_back = None
    pages_shown = []
    for i in range(first_page, last_page + 1):
        pages_shown.append(i)
    # Append proper character to url
    if url:
        # Remove existing page GET parameters
        url = unicode(url)
        url = re.sub(r'\?page\=[^\&]+', u'?', url)
        url = re.sub(r'\&page\=[^\&]+', u'', url)
        # Append proper separator
        if u'?' in url:
            url += u'&'
        else:
            url += u'?'
    # Append extra string to url
    if extra:
        if not url:
            url = u'?'
        url += unicode(extra) + u'&'
    if url:
        url = url.replace(u'?&', u'?')
    # Set CSS classes, see http://twitter.github.io/bootstrap/components.html#pagination
    pagination_css_classes = ['pagination']
    if size in ['small', 'large']:
        pagination_css_classes.append('pagination-%s' % size)
    if align == 'center':
        pagination_css_classes.append('pagination-centered')
    elif align == 'right':
        pagination_css_classes.append('pagination-right')
    # Build context object
    return {
        'bootstrap_pagination_url': url,
        'num_pages': num_pages,
        'current_page': current_page,
        'first_page': first_page,
        'last_page': last_page,
        'pages_shown': pages_shown,
        'pages_back': pages_back,
        'pages_forward': pages_forward,
        'pagination_css_classes': ' '.join(pagination_css_classes),
    }
