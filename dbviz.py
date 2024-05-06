import pg8000
from pg8000 import JSON
import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
import sys
import ga

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
arguments = sys.argv[1:]
args = {}
for idx, arg in enumerate(arguments):
    if arg.startswith('-'):
        key = arg
        if idx + 1 < len(arguments) and not arguments[idx + 1].startswith('-'):
            value = arguments[idx + 1]
        else:
            value = None
        args[key] = value


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

if args.get('-t'):
    table_name = args.get('-t').strip()
else:
    # get the latest table name with the max run_id
    cur.execute("SELECT table_name FROM runs WHERE run_id = (SELECT MAX(run_id) FROM runs)")
    table_name = cur.fetchone()[0]

start = 0
end = sys.maxsize

if args.get('-s'):
    start = int(args.get('-s'))
if args.get('-e'):
    end = int(args.get('-e'))
# Execute the SELECT query to fetch the table
cur.execute(f'SELECT * FROM {table_name} WHERE individual_id >= {start} AND individual_id <= {end} ORDER BY individual_id ASC')

# Fetch all rows from the result set
rows = cur.fetchall()

# Get the column names from the cursor description
column_names = [desc[0] for desc in cur.description]

# Create a DataFrame from the fetched data, order by individual_id
df = pd.DataFrame(rows, columns=column_names)

# get the row with the max fitness
max_fitness_row = df.loc[df['fitness'].idxmax()]

# Replace entries in ctrl_pts column with "JSON"
df['ctrl_pts'] = 'JSON Object'

if '-st' not in args:
    print(df.to_markdown(index=False))

# Print the individual with the max fitness, but make sure ctrl_pts is not truncated
print("The individual with the max fitness is:")
# remove the ctrl_pts column from the max_fitness_row and manually print it
print(max_fitness_row.drop('ctrl_pts'))
print("ctrl_pts: ", (max_fitness_row['ctrl_pts']))

if '-p' in args:

    if args.get('-p') is not None:
        individual_id = int(args.get('-p'))
        cur.execute(f'SELECT * FROM {table_name} WHERE individual_id = {individual_id}')
        row = cur.fetchone()
        if row is not None:
            print(row)
        else:
            print(f"Individual with ID {individual_id} not found")
    else:
        row = max_fitness_row
        print("Plotting the airfoil with the max fitness")

    # plot the airfoil
    if args.get('-plotfile'):
        print("Exported airfoil to {}".format(args.get('-plotfile')))
        ga.plot_fitpoints(np.array(max_fitness_row['ctrl_pts']), fpath=args.get('-plotfile'))
    else:
        ga.plot_fitpoints(np.array(max_fitness_row['ctrl_pts']))

if '-track' in args:
    
    gen_interval = 2

    if args.get('-track'):
        gen_interval = int(args.get('-track'))

    # plot the best airfoil for every generation, at gen_interval intervals
    cur.execute(f'''SELECT t.individual_id, t.ctrl_pts, t.fitness, t.generation_number
                FROM {table_name} t
                JOIN (
                    SELECT generation_number, MAX(fitness) AS max_fitness
                    FROM {table_name}
                    GROUP BY generation_number
                ) max_fitness_per_generation
                ON t.generation_number = max_fitness_per_generation.generation_number
                AND t.fitness = max_fitness_per_generation.max_fitness;''')
    rows = cur.fetchall()

    # plot the airfoil for each generation
    for idx, row in enumerate(rows):
        if idx % gen_interval == 0:
            print(f"#{row[0]} - Generation: {row[3]}, Fitness: {row[2]}")

            # if location to plot to is specified
            if args.get('-plotfile'):
                if args.get('-plotfile')[-1] != '/':
                    plotfile = args.get('-plotfile') + '/' + f"airfoil_{row[0]}_gen_{row[3]}.png"
                else:
                    plotfile = args.get('-plotfile') + f"airfoil_{row[0]}_gen_{row[3]}.png"

                ga.plot_fitpoints(np.array(row[1]), fpath=plotfile, title=f"#{row[0]} - Generation: {row[3]}, Fitness: {row[2]}")

            ga.plot_fitpoints(np.array(row[1]), title=f"#{row[0]} - Generation: {row[3]}, Fitness: {row[2]}")  



# Close cursor and connection
conn.close()
cur.close()