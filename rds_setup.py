import psycopg2


try:
    conn = psycopg2.connect( host=host, user=username, password=password, port=port, database=database )
    print("Database opened successfully")

    cur = conn.cursor()

    # Table - runs (if not exists)
    # run_id, time_started, time_completed, in-progress, table_name, shape, solver, optimizer
    # cur.execute('''
    #     CREATE TABLE IF NOT EXISTS runs (
    #         run_id SERIAL PRIMARY KEY,
    #         time_started TIMESTAMP,
    #         time_completed TIMESTAMP,
    #         in_progress BOOLEAN,
    #         completed BOOLEAN,
    #         table_name TEXT,
    #         shape TEXT,
    #         solver TEXT,
    #         optimizer TEXT
    #     );
    # ''')

    cur.execute('''
                INSERT INTO runs (run_id, time_started, in_progress, completed, table_name, shape, solver, optimizer)
                VALUES (7, NOW(), TRUE, FALSE, 'torus1', 'torus', 'simpleFoam', 'nlopt');
                ''')
    conn.commit()

    cur.execute("SELECT * FROM runs")
    rows = cur.fetchall()

    print(rows)

    conn.close()
except:
    print("I am unable to connect to the database")