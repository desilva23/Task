"""python -m datagen [--store demo|port] [--seed N] [--out DIR] — write a store's six CSVs."""

import argparse
from pathlib import Path

from datagen.build import DEFAULT_SEED, STORES, write_store

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--store", choices=sorted(STORES), default="demo")
parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
parser.add_argument("--out", type=Path)
args = parser.parse_args()
out = args.out or Path("data") / STORES[args.store]
write_store(out, args.seed, args.store)
print(f"wrote {out} (seed {args.seed})")
