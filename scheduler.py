import multiprocessing 
import time 
import numpy as np
import psycopg2
import os
import csv
import sys
from dotenv import load_dotenv
import json
from psycopg2.extras import Json
from psycopg2.extensions import register_adapter
from ga import genetic_alg
from cPointstoCMeshv3 import fix_boundary, salome_stuff

# configs
shape = 'airfoil'
solver = 'simpleFoam'
optimizer = 'GA'
total_generations = 100
population_size = 100
alpha = .00875

register_adapter(dict, Json)

load_dotenv()
host = os.getenv("RDS_HOST")
port = os.getenv("RDS_PORT")
database = os.getenv("RDS_DATABASE")
username = os.getenv("RDS_USERNAME")
password = os.getenv("RDS_PASSWORD")
print(host, port, database, username, password)

attempts = 0

# get number of cores
cores = multiprocessing.cpu_count()
print("Number of detected cores: {}".format(cores))

# converts control point formats from 3 coordinate lists to nested spline arrays
def coords_to_splines(xC, yC, zC, degree = 5):

    splines = []
    cur_spline = []

    for idx, elem in enumerate(xC):
        cur_spline.append([float(xC[idx]), float(yC[idx])])

        if idx % (degree + 1) == degree:
            splines.append(np.array(cur_spline))
            cur_spline = []

    return splines
   
def splines_to_coords(splines, degree = 5):

    xC = []
    yC = []
    zC = []

    for spline in splines:
        for coord in spline:
            xC.append(coord[0])
            yC.append(coord[1])
            zC.append(0.0)

    return xC, yC, zC

def airfoil_cost(input):
    '''
    Where input is control points in the splines format used by `ga.py`
    '''
    # convert splines to control points
    xC, yC, zC = splines_to_coords(input)

    # make sure we're in a core folder
    if 'core' not in os.getcwd() and 'runtime' not in os.getcwd():
        # assume we in root and default to core 0
        os.chdir('./runtime/core0')

    salome_stuff(xC, yC, zC, './constant/polyMesh')
    fix_boundary('./constant/polyMesh')

    # run the solver
    try:
        os.system('simpleFoam')
    except:
        print("Error running solver")
        # return a high cost
        return float('inf')
    
    # get the cl/cd
    with open('./postProcessing/forces/0/forceCoeffs.dat', 'r') as f:

        consider_csv = False
        coeff_csv = ''
        
        for line in f:
            if 'Cl' in line and 'Cd' in line:
                consider_csv = True

            if consider_csv:
                coeff_csv += line + '\n'


    # now we need to parse the csv
    reader = csv.reader(coeff_csv.split('\n'), delimiter='\t')    
    print(reader)
    cd = 2
    cl = 3
    # look at first row to see where Cd and Cl are
    for idx, row in enumerate(next(reader)):
        row = row.strip() 
        if row == 'Cd':
            cd = idx
        if row == 'Cl':
            cl = idx
    # go to last row to get the values
    for row in reader:
        if row:

            # in case tab delimiters didn't parse correctly
            if len(row) < 4:
                row = row[0].split(' ')
                row = [x for x in row if x]

            # store latest cl cd
            cd_val = row[cd]
            cl_val = row[cl]

    print(cd_val, cl_val)

    return float(cl_val) / float(cd_val)


def multiprocessor(parallel_eval, inputs, table_name, conn, cursor, gen_num):
    
    def to_execute(input):
        # add row to table
        cursor.execute('''INSERT INTO {} (time_started, in_progress, completed, generation_number, ctrl_pts)
                    VALUES (NOW(), TRUE, FALSE, {}, {});
                    '''.format(table_name, gen_num, input))
        conn.commit()

        # clean up this core's runtime folder (assumes that salome can overwrite files fine)
        # delete all folders except for base ones
        for file in os.listdir('./'):
            if file != '0' and file != 'constant' and file != 'system' and file != 'Allclean' and file != 'Allrun':
                os.system('rm -r ./{}'.format(file))
        
        # trigger core execute
        fitness, _ = parallel_eval(input)

        # update row in table that's not yet completed
        cursor.execute('''UPDATE {} SET time_completed = NOW(), in_progress = FALSE, completed = TRUE, cl_cd = {}
                    WHERE in_progress = TRUE AND generation_number = {} AND ctrl_pts = {};
                    '''.format(table_name, fitness, gen_num, input))
        conn.commit()

        return fitness, input
    
    # create process pool (manages allocation of processes to cores)
    pool = multiprocessing.Pool()

    # reroute to the correct runtime folder for each core
    template_folders = ['core{}'.format(i) for i in range(cores)]

    def reroute(input):
        os.chdir('./runtime/{}'.format(input))
    pool.map(reroute, template_folders)

    # execute the function in parallel
    outputs = pool.map(to_execute, inputs)
    pool.close()
    pool.join()

    print("Output: {}".format(outputs))
    return outputs

#-------------------------------------------------------------------

def initiate():

    global attempts     # attempts at db connection

    try: 
        conn = psycopg2.connect( host=host, user=username, password=password, port=port, database=database )
        print("Database opened successfully")


        
    except:
        # give it 3 chances to connect to the database
        attempts += 1
        if attempts < 3:
            print("I am unable to connect to the database. Trying again...")
            time.sleep(5)
            initiate()
        else:
            print("I am unable to connect to the database. Exiting...")
            exit()

    continue_execution(conn)

def continue_execution(conn = []):

    cur = conn.cursor()

    # Table - runs (if not exists)
    # run_id, time_started, time_completed, in-progress, table_name, shape, solver, optimizer
    cur.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            run_id SERIAL PRIMARY KEY,
            time_started TIMESTAMP,
            time_completed TIMESTAMP,
            in_progress BOOLEAN,
            completed BOOLEAN,
            table_name TEXT,
            shape TEXT,
            solver TEXT,
            optimizer TEXT,
            num_generations INTEGER,
            population_size INTEGER
        );
    ''')
    conn.commit()

    # get the latest run_id, and increment it by 1
    cur.execute("SELECT MAX(run_id) FROM runs")
    run_id = cur.fetchone()[0] + 1

    # add entry to runs table
    table_name = shape + optimizer + str(run_id) + ''
    print(table_name)
    cur.execute('''
                INSERT INTO runs (run_id, time_started, in_progress, completed, table_name, shape, solver, optimizer, num_generations, population_size)
                VALUES ({}, NOW(), TRUE, FALSE, '{}', '{}', '{}', '{}', {}, {});
                '''.format(run_id, table_name, shape, solver, optimizer, total_generations, population_size))
    conn.commit()

    # Table - airfoil (if not exists)
    # individual_id, time_started, time_completed, in-progress, completed, generation_number, cl-cd, ctrl_pts
    cur.execute('''
        CREATE TABLE IF NOT EXISTS {} (
            individual_id SERIAL PRIMARY KEY,
            time_started TIMESTAMP,
            time_completed TIMESTAMP,
            in_progress BOOLEAN,
            completed BOOLEAN,
            generation_number INTEGER,
            cl_cd FLOAT,
            ctrl_pts JSON
        );
    '''.format(table_name))
    conn.commit()

    # assuming that if you have cores # of folders, it's setup right, otherwise, delete and recreate
    if len(os.listdir('./runtime')) != cores + 1:   # cores + base file
        
        # delete all files in runtime folder
        for file in os.listdir('./runtime'):
            os.system('rm -r ./runtime/{}'.format(file))

        os.system('touch ./runtime/base')

        print("cleaned working directories")

        # create the necessary directories by copying the structure directory and all its contents to the runtime folder
        for i in range(cores):
            os.system('cp -r ./structure/airfoilOptTest1Clean ./runtime/core{}'.format(i))

        print("created working directories")
    else:
        print("Assumed runtime directories are already created")

    # get init population
    xC = []
    yC = []
    zC = []
    with open('./ControlPoints.txt') as f:
        reader = csv.reader(f, delimiter = "\t")
        for n in reader:
            if (n[0] == "START"): #ignore start lines
                pass
            elif (n[0] == "END"): #ignore end lines
                pass
            else:
                xC.append(n[0]) #add first number in each row to x coordinate list
                yC.append(n[1]) #add second number to y list
                zC.append(n[2]) #third to z list
        f.close()

    initial_splines = coords_to_splines(xC, yC, zC)

    # start GA
    genetic_alg(cost_fcn=airfoil_cost, multiprocessor=multiprocessor, conn=conn, cursor=cur, table_name=table_name, num_generations=total_generations, pop_size=population_size, alpha=alpha, init_pop_splines=initial_splines)

    # update the entry as completed
    cur.execute("UPDATE runs SET time_completed = NOW(), in_progress = FALSE, completed = TRUE WHERE table_name = '{}';".format(table_name))
    conn.commit()

    conn.close()

initiate()


# if __name__ == '__main__': 
#     fix_boundary('./base/airfoilOptTest1Clean/constant/polyMesh')
  
# def squared(x): 
#     time.sleep(5)
#     print(x*x)
#     return x * x 
   
# if __name__ == '__main__': 
#     pool = multiprocessing.Pool() 
#     pool = multiprocessing.Pool(processes=4) 
#     inputs = [0,1,2,3,4] 
#     outputs = pool.map(squared, inputs) 
#     print("Input: {}".format(inputs)) 
#     print("Output: {}".format(outputs)) 