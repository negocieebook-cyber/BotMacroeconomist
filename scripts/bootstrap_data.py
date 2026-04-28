from __future__ import annotations

from pathlib import Path

from collect.manual_ingest import ingest_manual_item


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    ingest_manual_item(
        base_dir,
        {
            "text": "Exemplo manual: inflação de serviços continua pressionando o núcleo.",
            "source": "bootstrap",
            "topic": "inflacao",
        },
    )
    print("Dados iniciais adicionados ao inbox manual.")


if __name__ == "__main__":
    main()
