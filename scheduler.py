import multiprocessing 
import time 
import numpy as np
import pg8000
import os
import csv
import sys
from time import sleep
from dotenv import load_dotenv
import json
from pg8000 import JSON
from ga import genetic_alg

# configs
shape = 'airfoil'
solver = 'simpleFoam'
optimizer = 'GA'
mesh_radius = 5
total_generations = 6
population_size = 8
alpha = .00875
slope_weight = 0.0
input_file = 'ControlPoints0012.txt'
# cores = multiprocessing.cpu_count()
cores = 1

# temp globals
conn = None
# cur = None
parallel_eval = lambda x: 9
table_name = shape + optimizer
gen_num = 0

# register_adapter(dict, Json)

load_dotenv()
host = os.getenv("RDS_HOST")
port = os.getenv("RDS_PORT")
database = os.getenv("RDS_DATABASE")
username = os.getenv("RDS_USERNAME")
password = os.getenv("RDS_PASSWORD")
salome_route = os.getenv("SALOME_LAUNCHER")
print(host, port, database, username, password)

# start the salome environment
if salome_route is not None:
    os.system("source {}".format(salome_route))
    print("Salome environment deployed")

from cPointstoCMeshv3 import fix_boundary, salome_stuff

attempts = 0

# get number of cores
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

def airfoil_cost(input, individual_id = None):
    '''
    Where input is control points in the splines format used by `ga.py`
    '''
    # convert splines to control points
    xC, yC, zC = splines_to_coords(input)

    # make sure we're in a core folder
    if 'core' not in os.getcwd() and 'runtime' not in os.getcwd():
        # assume we in root and default to core 0
        os.chdir('./runtime/core0')

    try:
        print("Running salome...")
        print(xC)
        print(yC)
        print(zC)
        salome_stuff(xC, yC, zC, './constant/polyMesh', mesh_radius=mesh_radius)
        fix_boundary('./constant/polyMesh')

        # suppress prints
        print("Running solver...suppressing output...")
        try:
            # run the solver
            os.system('simpleFoam >/dev/null')
        except:
            print("Error running solver")
            # return a high cost
            return float('inf')
    except:
        print("Error running salome")
        # sleep(5)
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

            # in case tab delimiters didn't parse correctly (happens on some systems)
            if len(row) < 4:
                row = row[0].split(' ')
                row = [x for x in row if x]

            # store latest cl cd
            cd_val = row[cd]
            cl_val = row[cl]

    print(cd_val, cl_val)

    if individual_id is not None:
        # update the row in the db
        conn.run("UPDATE {} SET cl = {}, cd = {} WHERE individual_id = {} AND in_progress = TRUE AND completed = FALSE;"\
            .format(table_name, float(cl_val), float(cd_val), individual_id))
        conn.commit()

    # return cd/cl since we're minimizing cost
    if float(cl_val) == 0:
        return float('inf')
    return (float(cd_val) / float(cl_val))

# # obtain the process id of the current process
# def get_pid(input):
#     print("PID: {}".format(os.getpid()))
#     return os.getpid()


# make multiprocessor function to run the solver in parallel (also has to be global for multiprocessing to work)
def to_execute(input):

    # print("Executing process {}...".format(os.getpid()))
    if 'core' not in os.getcwd() and 'runtime' not in os.getcwd():
        os.chdir('./runtime/core0')

    # make a version of the input that can be stored in the db (numpy arrays can't be stored)
    if isinstance(input, np.ndarray):
        input2 = input.tolist()
    else:
        input2 = input
    # do it for nested arrays
    for idx, elem in enumerate(input2):
        if isinstance(elem, np.ndarray):
            input2[idx] = elem.tolist()
        for idx2, elem2 in enumerate(elem):
            if isinstance(elem2, np.ndarray):
                input2[idx][idx2] = elem2.tolist()
    print("CLEAN CTRL PTS ", json.dumps(input2))

    # add row to table
    # could add all of a generation's rows at once to minimize I/O, but would have to update each row anyways
    # with time_started, so it doesn't reduce runtime network cost

    # get latest individual_id
    x = conn.run("SELECT MAX(individual_id) FROM {}".format(table_name))
    individual_id = x[0][0]
    if individual_id is None:
        individual_id = 1
    else:
        individual_id += 1

    conn.run('''INSERT INTO {} (individual_id, time_started, in_progress, completed, generation_number, ctrl_pts)
                VALUES ({}, NOW(), TRUE, FALSE, {}, CAST(:ct as jsonb));
                '''.format(table_name, individual_id, gen_num + 1), ct=json.dumps(input2))  # save as gen_num + 1 since we're starting from 0
    conn.commit()

    print("{} wrote to table {} individual number {}".format(os.getpid(), table_name, individual_id))

    # # make sure we're in a core folder
    if 'core' not in os.getcwd() and 'runtime' not in os.getcwd():
        # assume we in root and default to core 0
        print("In wrong folder - " + os.getcwd() + "; Redirecting to core0...")
        os.chdir('./runtime/core0')

    # clean up this core's runtime folder (assumes that salome can overwrite files fine)
    # delete all folders except for core ones
    print("Cleaning PID {}'s folders...".format(os.getpid()), end='')
    for file in os.listdir('./'):
        if file != '0' and file != 'constant' and file != 'system' and file != 'Allclean' and file != 'Allrun' and file != '.git':
            print(file, end=' ')
            os.system('rm -r ./{}'.format(file))
    print()
    
    # trigger core execute
    output = parallel_eval(input, individual_id)
    if output is None:
        fitness = -1.0
    else:
        fitness = output[0]

    # update row in table that's not yet completed using row-level locking
    conn.run("UPDATE {} SET time_completed = NOW(), in_progress = FALSE, completed = TRUE, fitness = {} WHERE individual_id = {} AND in_progress = TRUE AND completed = FALSE AND generation_number = {};"\
            .format(table_name, fitness, individual_id, gen_num + 1))   
    conn.commit()


    return fitness, input

def multiprocessor(parallel_eval_fcn, inputs, cur_table, conns, generation_number):

    # set globals
    global conn
    conn = conns
    global parallel_eval
    parallel_eval = parallel_eval_fcn
    global table_name
    table_name = cur_table
    global gen_num
    gen_num = generation_number
    
    # create process pool (manages allocation of processes to cores)
    pool = multiprocessing.Pool(processes=cores)

    # reroute to the correct runtime folder for each core
    # template_folders = ['core{}'.format(i) for i in range(cores)]
    # pids = pool.map(get_pid, template_folders)

    # execute the function in parallel
    # print(inputs)
    print("Starting parallel execution on {} cores...".format(len(inputs)))
    outputs = pool.map(to_execute, inputs)
    pool.close()
    pool.join()

    print("Output: {}".format(outputs))
    return outputs

#-------------------------------------------------------------------

def initiate():

    global attempts     # attempts at db connection
    global conn         # db connection

    try: 
        conn = pg8000.connect( host=host, user=username, password=password, port=port, database=database )
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

def continue_execution(conn):

    global table_name
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
            resolution FLOAT,
            num_generations INTEGER,
            population_size INTEGER
        );
    ''')
    conn.commit()

    # get the latest run_id, and increment it by 1
    x = conn.run("SELECT MAX(run_id) FROM runs")
    run_id = x[0][0]
    if run_id is None:
        run_id = 1
    else:
        run_id += 1

    # add entry to runs table
    table_name = shape + optimizer + str(run_id) + ''
    print(table_name)
    cur.execute('''
                INSERT INTO runs (run_id, time_started, in_progress, completed, table_name, shape, solver, optimizer, resolution, num_generations, population_size, learning_rate)
                VALUES ({}, NOW(), TRUE, FALSE, '{}', '{}', '{}', '{}', {}, {}, {}, {});
                '''.format(run_id, table_name, shape, solver, optimizer, mesh_radius, total_generations, population_size, alpha))
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
            fitness FLOAT,
            cl FLOAT,
            cd FLOAT,
            ctrl_pts JSON
        );
    '''.format(table_name))
    conn.commit()
    print("Table {} created".format(table_name))

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
    with open(input_file) as f:
        reader = csv.reader(f, delimiter = "\t")
        for n in reader:
            if (n[0] == "START"): #ignore start lines
                pass
            elif (n[0] == "END"): #ignore end lines
                pass
            else:
                xC.append(float(n[0])) #add first number in each row to x coordinate list
                yC.append(float(n[1])) #add second number to y list
                zC.append(float(n[2])) #third to z list
        f.close()
    print(xC)
    print(yC)
    print(zC)
    initial_splines = coords_to_splines(xC, yC, zC)
    print("Found initial splines: ", initial_splines)

    # print(os.getcwd())
    # # make a version of the input that can be stored in the db (numpy arrays can't be stored)
    # if isinstance(initial_splines, np.ndarray):
    #     input2 = initial_splines.tolist()
    # else:
    #     input2 = initial_splines
    # # do it for nested arrays
    # for idx, elem in enumerate(input2):
    #     if isinstance(elem, np.ndarray):
    #         input2[idx] = elem.tolist()
    #     for idx2, elem2 in enumerate(elem):
    #         if isinstance(elem2, np.ndarray):
    #             input2[idx][idx2] = elem2.tolist()
    # print("E", json.dumps(input2))

    # # run a simulation on the initial splines
    # if 'core' not in os.getcwd() and 'runtime' not in os.getcwd():
    #     os.chdir('./runtime/core0')

    # print("Cleaning PID {}'s folders...".format(os.getpid()), end='')
    # for file in os.listdir('./'):
    #     if file != '0' and file != 'constant' and file != 'system' and file != 'Allclean' and file != 'Allrun' and file != '.git':
    #         print(file, end=' ')
    #         os.system('rm -r ./{}'.format(file))
    # print()

    # # trigger core execute
    # conn.run('''INSERT INTO {} (individual_id, time_started, in_progress, completed, generation_number, ctrl_pts)
    #             VALUES (0, NOW(), TRUE, FALSE, 0, CAST(:ct as jsonb));
    #             '''.format(table_name), ct=json.dumps(input2))
    # conn.commit()
    # fitness = airfoil_cost(initial_splines, 0)
    # print("Initial fitness: ", fitness)
    # conn.run("UPDATE {} SET time_completed = NOW(), in_progress = FALSE, completed = TRUE, fitness = {} WHERE individual_id = 0 AND in_progress = TRUE AND completed = FALSE AND generation_number = 0;"\
    #         .format(table_name, fitness))
    # conn.commit()

    # for file in os.listdir('./'):
    #     if file != '0' and file != 'constant' and file != 'system' and file != 'Allclean' and file != 'Allrun' and file != '.git':
    #         print(file, end=' ')
    #         os.system('rm -r ./{}'.format(file))
    # print()

    # # revert to root directory and undo changes
    # print(os.getcwd())
    # os.chdir('../..')
    # print(os.getcwd())
    
    # start GA
    genetic_alg(cost_fcn=airfoil_cost, multiprocessor=multiprocessor, conn=conn, table_name=table_name, num_generations=total_generations, pop_size=population_size, alpha=alpha, init_pop_splines=initial_splines, slope_weight=slope_weight)

    # update the entry as completed
    conn.run("UPDATE runs SET time_completed = NOW(), in_progress = FALSE, completed = TRUE WHERE table_name = '{}';".format(table_name))
    conn.commit()

    if conn:
        conn.close()
    if cur:
        cur.close()

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