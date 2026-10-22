# database_migrations.py

from sqlalchemy import inspect, text


def migration_001_add_evaluation_mode(db):
    """Add evaluation_mode to fields if it does not exist."""
    inspector = inspect(db.engine)
    columns = {c["name"] for c in inspector.get_columns("fields")}

    if "evaluation_mode" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("""
                ALTER TABLE fields
                ADD COLUMN evaluation_mode
                VARCHAR(30) NOT NULL DEFAULT 'section_average'
            """))
        print("Migration 001 completed.")
    else:
        print("Migration 001 already applied.")


def migration_002_add_logger_port_map(db):
    """Add port_map to loggers if it does not exist."""
    inspector = inspect(db.engine)
    columns = {c["name"] for c in inspector.get_columns("loggers")}

    if "port_map" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("""
                ALTER TABLE loggers ADD COLUMN port_map JSON
            """))
        print("Migration 002 completed.")
    else:
        print("Migration 002 already applied.")


def migration_003_add_irrigation_execution_columns(db):
    """Add Arduino command and execution-status columns to irrigation_logs."""
    table_name = "irrigation_logs"
    inspector = inspect(db.engine)

    if not inspector.has_table(table_name):
        print(
            f"Migration 003 skipped: table '{table_name}' does not exist."
        )
        return

    columns = {c["name"] for c in inspector.get_columns(table_name)}

    new_columns = {
        "command_id": "VARCHAR(100)",
        "pot_number": "INTEGER",
        "valve": "INTEGER",
        "execution_status": "VARCHAR(30)",
        "execution_message": "VARCHAR(255)",
        "execution_started_at": "DATETIME",
        "execution_completed_at": "DATETIME",
        "actual_liters": "FLOAT",
        "runtime_seconds": "INTEGER",
    }

    with db.engine.begin() as connection:
        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                connection.execute(text(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {column_name} {column_type}"
                ))
                print(f"Added {table_name}.{column_name}")

    # Create a unique index so one Arduino command maps to one log.
    # SQLite allows multiple NULL values in a unique index.
    with db.engine.begin() as connection:
        connection.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            ux_irrigation_logs_command_id
            ON irrigation_logs (command_id)
        """))

    print("Migration 003 completed or already applied.")


def run_migrations(db):
    migration_001_add_evaluation_mode(db)
    migration_002_add_logger_port_map(db)
    migration_003_add_irrigation_execution_columns(db)