"""Registra o banco Censo Escolar 2022 no Apache Superset."""

from __future__ import annotations

import json

from superset.app import create_app


def main() -> None:
    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.core import Database

        URI = "postgresql+psycopg2://superset:superset@host.containers.internal:5432/censo_escolar"
        NAME = "Censo Escolar 2022"
        existing = db.session.query(Database).filter_by(database_name=NAME).one_or_none()
        if existing is None:
            database = Database(database_name=NAME)
            database.set_sqlalchemy_uri(URI)
            database.extra = json.dumps(
                {
                    "allows_virtual_table_explore": True,
                    "metadata_params": {},
                    "engine_params": {},
                    "schemas_allowed_for_file_upload": ["public"],
                }
            )
            db.session.add(database)
            db.session.commit()
            print("created", NAME, "id=", database.id)
        else:
            existing.set_sqlalchemy_uri(URI)
            db.session.commit()
            print("updated", NAME, "id=", existing.id)


if __name__ == "__main__":
    main()
