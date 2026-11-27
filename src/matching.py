"""Deterministic candidate generation and scoring; scores are not probabilities."""
import re
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
    return ' '.join(re.sub(r'[^\w\s]', ' ', value.casefold()).split())


def name_key(value: str) -> str:
    return re.sub(r'\b(limited|ltd|plc|llp)$', '', normalize(value)).strip()


def postcode_key(value: str) -> str:
    return re.sub(r'\s+', '', value.upper())


def address_key(value: str) -> str:
    return re.sub(r'\b(st|rd|ave)\b', lambda m: {'st':'street','rd':'road','ave':'avenue'}[m[0]], normalize(value))


def keys(record: Record) -> set[str]:
    p = postcode_key(record.postcode)
    n = name_key(record.name).split()
    return ({'p:'+p[:-3]} if len(p)>3 else set()) | ({'n:'+n[0]} if n else set())


class CandidateIndex:
    def __init__(self, records: Iterable[Record]):
        self.index: dict[str, list[Record]] = defaultdict(list)
        for record in records:
            for key in keys(record):
                self.index[key].append(record)

    def candidates(self, record: Record) -> list[Record]:
        found = {r.id:r for k in keys(record) for r in self.index.get(k, [])}
        return [found[k] for k in sorted(found)]


def score(a: Record, b: Record) -> float:
    n1, n2 = name_key(a.name), name_key(b.name)
    a1, a2 = address_key(a.address), address_key(b.address)
    p1, p2 = postcode_key(a.postcode), postcode_key(b.postcode)
    return round(0.55*(fuzz.ratio(n1,n2) if n1 and n2 else 0) + 0.30*(fuzz.ratio(a1,a2) if a1 and a2 else 0) + 15*bool(p1 and p1==p2), 2)


def decision(value: float) -> str:
    return 'auto_match' if value >= 90 else 'review' if value >= 65 else 'no_match'
