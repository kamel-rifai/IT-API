from sqlalchemy import create_engine, text, inspect

DB_URL = "postgresql+psycopg2://postgres:postgres@192.168.88.100:5433/planka"

engine = create_engine(DB_URL)

def list_public_tables():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"))
        return [r[0] for r in res]


def describe_table(table_name):
    inspector = inspect(engine)
    try:
        cols = inspector.get_columns(table_name, schema='public')
        return cols
    except Exception as e:
        return str(e)


def fetch_by_id(table_name, id_value):
    with engine.connect() as conn:
        try:
            q = text(f"SELECT * FROM public.\"{table_name}\" WHERE id = :id LIMIT 1")
            res = conn.execute(q, {"id": id_value}).mappings().fetchone()
            return dict(res) if res else None
        except Exception as e:
            return str(e)


if __name__ == '__main__':
    print("Connecting to DB and listing public tables...")
    tables = list_public_tables()
    print(f"Found {len(tables)} tables. Sample: {tables[:30]}\n")

    # Look for tables that may be relevant
    candidates = [t for t in tables if any(x in t for x in ['project', 'projects', 'board', 'boards', 'list', 'lists'])]
    print("Candidate tables:", candidates)

    # Describe the candidate tables
    for t in candidates:
        print('\n---', t, '---')
        cols = describe_table(t)
        print(cols)

    # Describe the card table and show sample cards in the target list
    print('\n--- card ---')
    print(describe_table('card'))
    with engine.connect() as conn:
        res = conn.execute(text("SELECT id, name, description, list_id, created_at FROM public.card WHERE list_id = :lid ORDER BY created_at DESC LIMIT 5"), {'lid': 1700907504793290333}).mappings().fetchall()
        print('Sample cards in list:', [dict(r) for r in res])

    # Check for provided ids
    ids = {
        'project': 1700906029732070999,
        'board': 1700906101530166873,
        'list': 1700907504793290333,
    }

    for label, idval in ids.items():
        print(f"\nSearching for {label} with id {idval} in candidate tables...")
        for t in candidates:
            row = fetch_by_id(t, idval)
            if row:
                print(f"Found in {t}: \n", row)
            # else: print(f"Not found in {t}")

    print('\nDone.')
