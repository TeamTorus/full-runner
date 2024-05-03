import pg8000
from pg8000 import JSON
import os
import json
from dotenv import load_dotenv

load_dotenv()
host = os.getenv("RDS_HOST")
port = os.getenv("RDS_PORT")
database = os.getenv("RDS_DATABASE")
username = os.getenv("RDS_USERNAME")
password = os.getenv("RDS_PASSWORD")
print(host, port, database, username, password)

conn = None
cur = None

try:
    
    conn = pg8000.connect( host=host, user=username, password=password, port=port, database=database )
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
    #         optimizer TEXT,
    #         num_generations INTEGER,
    #         population_size INTEGER
    #     );
    # ''')
    # conn.commit()

    # cur.execute('''
    #             INSERT INTO runs (run_id, time_started, in_progress, completed, table_name, shape, solver, optimizer)
    #             VALUES (9, NOW(), TRUE, FALSE, 'torus1', 'torus', 'simpleFoam', 'nlopt');
    #             ''')
    # conn.commit()

    # cur.execute("SELECT * FROM runs")
    # rows = cur.fetchall()

    # print(rows)

    # cur.execute("SELECT * FROM runs")
    # rows = cur.fetchall()

    # for row in rows:
    #     print(row)

    # cur.execute("SELECT * FROM airfoilGA11")
    # rows = cur.fetchall()
    # for row in rows:
    #     print(row)

    # delete table
    # cur.execute("DROP TABLE IF EXISTS runs")
    # conn.commit()

except:
    print("I am unable to connect to the database")
    exit()

input2 = [[[1.0091915219002996, 0.0010639316120454102], [0.9762709354828769, -0.012376864361881975], [0.793172482863676, -0.030771734654911294], [0.563300809443389, -0.04822340267397582], [0.38774576615590833, -0.07086701482546623], [0.1727422921002494, -0.06235680563106003]], [[0.1727422921002494, -0.06235680563106003], [0.11513860762621192, -0.0429925918764531], [-0.07627952286917314, -0.044778855096653476], [-0.06586899856316893, 0.03852052506894234], [0.10415519030321199, 0.042235863327795435], [0.18279151247869374, 0.06369668081656343]], [[0.18279151247869374, 0.06369668081656343], [0.3807460143229448, 0.0674044946417462], [0.573056293453547, 0.049086318264560225], [0.797318944273619, 0.03016493785692161], [0.9650422984389336, 0.00019777476482758737], [1.0091915219002996, 0.0010639316120454102]]]
print(type(json.dumps(input2)))
conn.run("INSERT INTO airfoilGA43 (ctrl_pts) VALUES (CAST(:ct as jsonb));", ct=json.dumps(input2))

cur.execute("SELECT * FROM airfoilGA43")
rows = cur.fetchall()
for row in rows:
    print(row)

x = conn.run("SELECT MAX(run_id) FROM runs")
print(x[0][0])

# conn.run('''INSERT INTO {} (individual_id, time_started, in_progress, completed, generation_number, ctrl_pts)
#                 VALUES ({}, NOW(), TRUE, FALSE, {}, CAST(:ct as jsonb));
#                 '''.format(table_name, individual_id, gen_num), ct=json.dumps(input2))

conn.close()