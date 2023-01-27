from django import template
from osmosis.models import TokenName
register = template.Library()

@register.filter
def token_alias(value):
    return TokenName.get_name(value)