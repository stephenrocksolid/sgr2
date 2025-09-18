"""
Shared search utilities for inventory models.
"""
import re
from django.db.models import Q

TOKEN_RE = re.compile(r'''(?P<key>\w+):(?P<val>"[^"]+"|\S+)''')

def parse_query(q: str):
    """
    Parse search query into tokens and generic terms.
    
    Args:
        q: Search query string
        
    Returns:
        tuple: (tokens, generic_terms) where tokens are (key, value) pairs
               and generic_terms are leftover words to search across all fields
    """
    q = (q or "").strip()
    tokens = [(m.group('key').lower(), m.group('val').strip('"')) for m in TOKEN_RE.finditer(q)]
    spans = [m.span() for m in TOKEN_RE.finditer(q)]
    
    # crude leftover words as generics
    used = set()
    for s, e in spans:
        used.update(range(s, e))
    
    generic = []
    buff = []
    for i, ch in enumerate(q):
        if i in used:
            if buff:
                generic.append("".join(buff).strip())
                buff = []
            continue
        buff.append(ch)
    
    if buff:
        generic.append("".join(buff).strip())
    
    # split leftover by whitespace
    generic_terms = [t for part in generic for t in part.split() if t]
    return tokens, generic_terms

def apply_tokens(qs, tokens, key_map):
    """
    Apply fielded search tokens to queryset.
    
    Args:
        qs: Django queryset
        tokens: List of (key, value) tuples from parse_query
        key_map: Dictionary mapping keys to field lookups
        
    Returns:
        Filtered queryset
    """
    if not tokens:
        return qs
    
    expr = Q()
    for k, v in tokens:
        field = key_map.get(k)
        if field:
            expr &= Q(**{field: v})
    return qs.filter(expr) if expr else qs.none()

def apply_generics(qs, terms, fields):
    """
    Apply generic search terms to queryset.
    
    Args:
        qs: Django queryset
        terms: List of generic search terms
        fields: List of field lookups to search across
        
    Returns:
        Filtered queryset
    """
    if not terms:
        return qs
    
    g = Q()
    for term in terms:
        inner = Q()
        for f in fields:
            inner |= Q(**{f: term})
        g &= inner  # every generic term must match somewhere
    return qs.filter(g)
