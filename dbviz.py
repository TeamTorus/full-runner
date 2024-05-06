import pg8000
from pg8000 import JSON
import os
import json
import pandas as pd
from dotenv import load_dotenv
import sys

load_dotenv()
host = os.getenv("RDS_HOST")
port = os.getenv("RDS_PORT")
database = os.getenv("RDS_DATABASE")
username = os.getenv("RDS_USERNAME")
password = os.getenv("RDS_PASSWORD")
print(host, port, database, username, password)

conn = None
cur = None

# extract all system arguments and flags
args = sys.argv[1:]
aguments = {}
for idx, arg in enumerate(args):
    if arg.startswith('-'):
        key = arg
        if idx + 1 < len(args) and not args[idx + 1].startswith('-'):
            value = args[idx + 1]
        else:
            value = None

try:
    
    conn = pg8000.connect( host=host, user=username, password=password, port=port, database=database )
    print("Database opened successfully")

    cur = conn.cursor()

except Exception as e:
    print('I am unable to connect to the database')
    print(e)
    if conn:
        conn.rollback()
    raise e

# get the latest table name with the max run_id
cur.execute("SELECT table_name FROM runs WHERE run_id = (SELECT MAX(run_id) FROM runs)")
table_name = cur.fetchone()[0]
# table_name = 'airfoilGA53'

# Execute the SELECT query to fetch the table
cur.execute(f'SELECT * FROM {table_name}')

# Fetch all rows from the result set
rows = cur.fetchall()

# Get the column names from the cursor description
column_names = [desc[0] for desc in cur.description]

# Create a DataFrame from the fetched data, order by individual_id
df = pd.DataFrame(rows, columns=column_names).sort_values(by='individual_id')

# get the row with the max fitness
max_fitness_row = df.loc[df['fitness'].idxmax()]

# Replace entries in ctrl_pts column with "JSON"
df['ctrl_pts'] = 'JSON Object'

print(df.to_markdown(index=False))

# Print the individual with the max fitness, but make sure ctrl_pts is not truncated
print("The individual with the max fitness is:")
# remove the ctrl_pts column from the max_fitness_row and manually print it
print(max_fitness_row.drop('ctrl_pts'))
print("ctrl_pts: ", (max_fitness_row['ctrl_pts']))

# Close cursor and connection
conn.close()
cur.close()
