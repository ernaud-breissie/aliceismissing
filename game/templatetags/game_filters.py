from django import template
from django.db.models import QuerySet
from itertools import chain

register = template.Library()

@register.filter
def filter(queryset, field):
    """
    Filter a queryset by field being truthy
    Usage: {{ messages|filter:"image" }}
    """
    if not queryset or not hasattr(queryset, 'filter'):
        return queryset
    
    return queryset.filter(**{field: True})

@register.filter
def add(queryset1, queryset2):
    """
    Combine two querysets
    Usage: {{ location_cards|add:suspect_cards }}
    """
    if isinstance(queryset1, QuerySet) and isinstance(queryset2, QuerySet):
        # If both are querysets, combine them
        return list(chain(queryset1, queryset2))
    
    # If one of them is already a list (from a previous add operation)
    if isinstance(queryset1, list):
        if isinstance(queryset2, QuerySet):
            return list(chain(queryset1, queryset2))
        elif isinstance(queryset2, list):
            return queryset1 + queryset2
    
    # If first is a queryset and second is a list
    if isinstance(queryset1, QuerySet) and isinstance(queryset2, list):
        return list(chain(queryset1, queryset2))
    
    # Return first if we can't combine them
    return queryset1

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key
    
    Usage: {{ dictionary|get_item:key }}
    """
    if not dictionary:
        return []
    
    # Convert to int if it's a number string (for integer keys)
    if isinstance(key, str) and key.isdigit():
        key = int(key)
    
    # Return the value or an empty list if not found
    return dictionary.get(key, [])

@register.filter
def selectattr(iterable, attr):
    """
    Filter a list of objects by an attribute being truthy
    
    Usage: {{ list|selectattr:"revealed" }}
    """
    if not iterable:
        return []
    
    result = []
    for item in iterable:
        try:
            value = getattr(item, attr)
            if value:
                result.append(item)
        except (AttributeError, TypeError):
            pass
    
    return result

