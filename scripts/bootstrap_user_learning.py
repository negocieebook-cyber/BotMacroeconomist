from pathlib import Path

from learn.bootstrap_user_context import bootstrap_user_learning


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1]
    summary = bootstrap_user_learning(base_dir)
    print(summary)
