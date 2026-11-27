"""Deterministic candidate generation and scoring; scores are not probabilities."""
import re
import unicodedata
from collections import defaultdict
from typing import Iterable
from pydantic import BaseModel, Field
from rapidfuzz import fuzz

class Record(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=500)
    address: str = Field(default='', max_length=1000)
    postcode: str = Field(default='', max_length=20)


def normalize(value: str) -> str:
    value = unicodedata.normalize('NFKC', value).casefold()
    return ' '.join(re.sub(r'[^\w\s]', ' ', value).split())


def name_key(value: str) -> str:
    return re.sub(r'(?:\b(?:limited|ltd|plc|llp)\s*)+$', '', normalize(value)).strip()


def postcode_key(value: str) -> str:
    return re.sub(r'\s+', '', value.upper())


def address_key(value: str) -> str:
    return re.sub(r'\b(st|rd|ave)\b', lambda m: {'st':'street','rd':'road','ave':'avenue'}[m[0]], normalize(value))


STOP_WORDS = {'the', 'and', 'of', 'a', 'an'}
MAX_CANDIDATES = 200


def name_prefix(value: str) -> str:
    return next((token[:4] for token in name_key(value).split() if token not in STOP_WORDS), '')


def keys(record: Record) -> set[str]:
    """Multiple blocking passes; exact postcode and name/district are stronger."""
    p = postcode_key(record.postcode)
    prefix = name_prefix(record.name)
    found = {'p:' + p} if len(p) > 3 else set()
    if prefix:
        found.add('n:' + prefix)
        if len(p) > 3:
            found.add('pn:' + p[:-3] + ':' + prefix)
    return found


class CandidateIndex:
    def __init__(self, records: Iterable[Record], limit: int = MAX_CANDIDATES):
        if limit < 1:
            raise ValueError('Candidate limit must be positive')
        self.limit = limit
        self.index: dict[str, list[Record]] = defaultdict(list)
        for record in records:
            for key in keys(record):
                self.index[key].append(record)

    def candidates(self, record: Record) -> list[Record]:
        # Exact postcode and prefix+district beat the global prefix fallback.
        # Cap expensive scoring, not the initial bucket lookups.
        found: dict[str, Record] = {}
        for key in sorted(keys(record), key=lambda k: (0 if k.startswith('p:') else 1 if k.startswith('pn:') else 2, k)):
            for candidate in self.index.get(key, []):
                found[candidate.id] = candidate
        p = postcode_key(record.postcode)
        prefix = name_prefix(record.name)
        def rank(candidate: Record) -> tuple[bool, bool, bool, str]:
            cp = postcode_key(candidate.postcode)
            same_prefix = bool(prefix and prefix == name_prefix(candidate.name))
            same_postcode = bool(p and p == cp)
            same_district = bool(len(p) > 3 and p[:-3] == cp[:-3])
            return (not (same_postcode and same_prefix), not same_postcode,
                    not (same_prefix and same_district), candidate.id)
        return sorted(found.values(), key=rank)[:self.limit]


def score(a: Record, b: Record) -> float:
    n1, n2 = name_key(a.name), name_key(b.name)
    a1, a2 = address_key(a.address), address_key(b.address)
    p1, p2 = postcode_key(a.postcode), postcode_key(b.postcode)
    return round(0.55*(fuzz.ratio(n1,n2) if n1 and n2 else 0) + 0.30*(fuzz.ratio(a1,a2) if a1 and a2 else 0) + 15*bool(p1 and p1==p2), 2)


def decision(value: float) -> str:
    return 'auto_match' if value >= 90 else 'review' if value >= 65 else 'no_match'
