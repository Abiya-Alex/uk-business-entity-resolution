"""Create a deterministic, unlabelled candidate sample for manual review."""
import argparse
import csv
import random
from src.matching import CandidateIndex, Record, score


def records(path: str) -> list[Record]:
    with open(path, encoding='utf-8-sig', newline='') as f:
        return [Record.model_validate(row) for row in csv.DictReader(f)]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('companies'); p.add_argument('fsa'); p.add_argument('output')
    p.add_argument('--count', type=int, default=200)
    args = p.parse_args()
    rng = random.Random(42)
    companies = records(args.companies)
    premises = records(args.fsa)
    index = CandidateIndex(companies)
    rng.shuffle(premises)
    fields = ['a_name','a_address','a_postcode','b_name','b_address','b_postcode','label','a_id','b_id','evidence']
    written = 0
    with open(args.output, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for premise in premises:
            if written >= args.count:
                break
            candidates = index.candidates(premise)
            if not candidates:
                continue
            # Cycle between strongest candidates and other plausible negatives.
            candidate = max(candidates, key=lambda c: score(premise,c)) if written % 2 == 0 else rng.choice(candidates)
            writer.writerow(dict(a_name=premise.name,a_address=premise.address,a_postcode=premise.postcode,b_name=candidate.name,b_address=candidate.address,b_postcode=candidate.postcode,label='',a_id=premise.id,b_id=candidate.id,evidence=''))
            written += 1
    print(f'Wrote {written} unlabelled candidate pairs; add independently found missed-block positives before evaluation.')

if __name__ == '__main__':
    main()
