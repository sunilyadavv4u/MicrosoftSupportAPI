import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.store import initialize_from_csv

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description="Load CSV datasets into the local SQLite mock API store.")
    parser.add_argument("--reload",action="store_true",help="Drop and reload all source tables from CSV.")
    args=parser.parse_args()
    counts=initialize_from_csv(reload=args.reload)
    print("\nLoaded source row counts:")
    for table,count in counts.items():
        print(f"{table}: {count:,}")
    print(f"TOTAL: {sum(counts.values()):,}")
