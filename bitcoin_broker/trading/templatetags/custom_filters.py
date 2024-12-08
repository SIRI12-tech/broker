from django import template
import hashlib

register = template.Library()

@register.filter
def md5(value):
    """Converts a string to its MD5 hash"""
    if value is None:
        return ""
    return hashlib.md5(str(value).encode('utf-8')).hexdigest()
