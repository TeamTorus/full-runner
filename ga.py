import numpy as np
import scipy.interpolate as si
import matplotlib.pyplot as plt
import sys
from shapely.validation import make_valid
from shapely.geometry import Polygon

def scipy_bspline(cv, n=100, degree=5, periodic=False):
    """ Calculate n samples on a bspline

        cv :      Array ov control vertices
        n  :      Number of samples to return
        degree:   Curve degree
        periodic: True - Curve is closed
    """
    cv = np.asarray(cv)
    count = cv.shape[0]

    # Closed curve
    if periodic:
        kv = np.arange(-degree,count+degree+1)
        factor, fraction = divmod(count+degree+1, count)
        cv = np.roll(np.concatenate((cv,) * factor + (cv[:fraction],)),-1,axis=0)
        degree = np.clip(degree,1,degree)

    # Opened curve
    else:
        degree = np.clip(degree,1,count-1)
        kv = np.clip(np.arange(count+degree+1)-degree,0,count-degree)
    # Return samples
    max_param = count - (degree * (1-periodic))
    spl = si.BSpline(kv, cv, degree)
    return spl(np.linspace(0,max_param,n))

# Returns flattened list of fitpoints as a list of tuple-points
def get_fitpoints(splines):
    points = []
    for s in splines:
        points.append(scipy_bspline(s, n=50, degree=5, periodic=False))
        
    tuples = []
    for spline in points:
        flattened_points = spline.reshape(-1, 2).tolist()
        flattened_tuples = [tuple(point) for point in flattened_points]
        tuples.append(flattened_tuples)
    tuples = [point for tup in tuples for point in tup]
    
    return tuples  


def plot_fitpoints(splines, show_points=True, fpath=None):
    for s in range(len(splines)): 
        if show_points == True:
            plt.plot(splines[s][:,0], splines[s][:,1], 'o--', label=f'Spline {s+1}')
        p = scipy_bspline(splines[s], n=50, degree=5, periodic=False)
        x,y = p.T
        # Setting equal aspect ratio for both axes to avoid distortion
        plt.axis('equal')
        plt.plot(x,y,)
        if fpath is not None:
            plt.savefig(fpath)
        
        
#--------------GA ALG--------------------
def genetic_alg(cost_fcn, multiprocessor = None, num_generations = 100, pop_size = 100, alpha = 0.00875, init_pop_splines = [], table_name = None, conn = None, slope_weight = 0):
    """
    Executes the genetic algorithm. Pass in a function that takes in an evaluation func and inputs list into `multiprocessor`
    for parallel compute, which should not be async and be blocking. If this is done, it should return the ranks list. 
    """

    # Gets difference in slopes between control points
    def slopes(splines):
        # List of the coordinates of the control points
        coordinates = []
        for s in splines:
            for coord in range(len(s)-1):
                coordinates.append(s[coord])
        # List of absolute value of slopes between the coordinates of the control points
        slopes = []
        for c in range(len(coordinates)):
            if c < len(coordinates)-1:
                slopes.append((coordinates[c+1][1]-coordinates[c][1])/(coordinates[c+1][0]-coordinates[c][0]))
            else:
                slopes.append((coordinates[0][1]-coordinates[c][1])/(coordinates[0][0]-coordinates[c][0]))
        return slopes

    # Fitness function to lead us to a fitted NACA0012
    def fitness(control_points, individual_id=None):
        cd_cl = cost_fcn(control_points, individual_id)
        # If area matches exactly, best shape is found
        if cd_cl == 0:
            return sys.maxsize
        # If not, add slopiness of the control points as a factor (shapes that are less slopy everywhere besides the leading edge are favored)
        else:
            sl = slopes(control_points)
            leading_slope = sl[7]
            slopiness = 0
            for d in sl:
                slopiness += abs(d)
            # Don't count slope of leading edge
            slopiness -= leading_slope

            slope_fitness = slope_weight * (1/slopiness + leading_slope)
            return (1/cd_cl + slope_fitness)

    # Crossover function
    def cross(p1, p2):
        new_p1 = p1
        new_p2 = p2
        # Switch every other point
        for s in range(len(p1)):
            for p in range(len(p1[s])):
                if p%2 == 0:
                    new_p1[s][p] = p2[s][p]
                    new_p2[s][p] = p1[s][p]
        # Make first coord of first spline and last coord of last spline the same
        new_p1[len(new_p1)-1][len(new_p1[len(new_p1)-1])-1] = new_p1[0][0]
        new_p2[len(new_p2)-1][len(new_p2[len(new_p2)-1])-1] = new_p2[0][0]
        # Make last coord of each spline and first coord of the next spline equal
        for spline_ct in range(1, len(new_p1)):
            new_p1[spline_ct][0] = new_p1[spline_ct-1][len(new_p1[spline_ct-1])-1]
            new_p2[spline_ct][0] = new_p2[spline_ct-1][len(new_p2[spline_ct-1])-1]
        return [new_p1, new_p2]

    # Mutation function for variation (less mutation as generation increases)
    def mut_func(num, gen):
        decay = (1-gen/num_generations)
        return (num + np.random.uniform(-alpha*decay, alpha*decay)) * np.random.uniform(1-alpha*decay, 1+alpha*decay)

    # Mutates a shape
    def mut(splines, gen):
        mut_shape = []
        for jdx, s in enumerate(splines):
            mut_spline_list = []
            for idx, point in enumerate(s):
                mut_point = []
                for coord in point:
                    # exempt knot on trailing edge
                    if idx == 0 and jdx == 0:
                        mut_point.append(coord)
                    elif idx == len(s)-1 and jdx == len(splines)-1:
                        mut_point.append(coord)
                    else:
                        mut_point.append(mut_func(coord, gen))
                mut_spline_list.append(mut_point)
            mut_spline = np.array(mut_spline_list)
            mut_shape.append(mut_spline)
        # Make first coord of first spline and last coord of last spline the same
        mut_shape[len(mut_shape)-1][len(mut_shape[len(mut_shape)-1])-1] = mut_shape[0][0]
        # Make last coord of each spline and first coord of the next spline equal
        for spline_ct in range(1, len(mut_shape)):
            mut_shape[spline_ct][0] = mut_shape[spline_ct-1][len(mut_shape[spline_ct-1])-1]
        return mut_shape

    # Generates an initial population of shapes by slightly mutating the control points of the unoptimized airfoil
    def init_pop(splines):
        pop = []
        for _ in range(pop_size):
            mutated = mut(splines, 0)
            if is_valid(mutated):
                pop.append(mutated)
        print("INITIAL POPULATION")
        print(pop)
        return pop

    # Checks the validity of the shape
    def is_valid(shape):
        coords = get_fitpoints(shape)
        p = Polygon(coords)
        return type(make_valid(p)) == type(p)

    # Creates a list containing the members of the population in order from most to least fit
    def rank(splines, generation_number):
        ranks = []

        # define potential parallel computation
        def parallel_eval(shape, individual_id=None):
            if is_valid(shape):
                return fitness(shape, individual_id), shape
            else:
                return None
            
        # if multiprocessing is enabled or not
        if multiprocessor == None:
            for shape in splines:
                val = parallel_eval(shape)
                if val is not None:
                    ranks.append(val)
        else:
            ranks = multiprocessor(parallel_eval_fcn=parallel_eval, inputs=splines, cur_table=table_name, conns=conn, generation_number=generation_number)

        # Rank solutions in reverse sorted order
        ranks.sort()
        ranks.reverse()
        return ranks

    # Gives the number in the nearest 8 decimal points
    def fmt(num):
        return "{:.8f}".format(round(num, 8))

    # Creates a new file in the current directory containing the formatted coordinates of the control points
    def save_ctrlpts(splines, gen):
        # Create a new file
        with open(f'Gen{gen+1} CtrlPts.txt', 'w') as file:
        # Write to the file
            for s in range(len(splines)):
                file.write("START\n")
                for coord in splines[s]:
                    file.write(fmt(coord[0])+"\t"+fmt(coord[1])+"\t"+fmt(0.0)+"\n")
                file.write("END\n")


    # Initial population
    cur_pop = init_pop(init_pop_splines)
    ranking = rank(cur_pop, 0)

    # Print the control points of the best solution in the initial population
    print(f"Generation 0 best solution is:")
    print(ranking[0])

    # Plot the fitpoints and control points of the initial population
    # fig, ax = plt.subplots()
    # plt.title(f"Generation 0")
    # plot_fitpoints(ranking[0][1], show_points=True)
    # plot_polygon(ax, airfoil_points, 'Airfoil')

    for i in range(num_generations):
        # Create the next generation
        next_gen = []

        # Choose the top 2 most fit shapes to keep in the next generation
        next_gen.append(ranking[0][1])
        next_gen.append(ranking[1][1])

        # Use tournament selection to find parents that will crossover and mutate to create the next generation
        for _ in range(pop_size//2-1):
            # Perform tournament selection on a random fourth of the population
            ranking_cpy = ranking
            np.random.shuffle(ranking_cpy)
            tournament_shapes = ranking_cpy[:len(ranking_cpy)//4]
            tournament_shapes.sort()
            tournament_shapes.reverse()
            # Choose 2 most fit parents in the random selection
            p1 = tournament_shapes[0][1]
            p2 = tournament_shapes[1][1]
            # Perform crossover
            crossed = cross(p1, p2)
            c1 = crossed[0]
            c2 = crossed[1]
            # Perform mutation
            c1 = mut(c1, i)
            c2 = mut(c2, i)
            # Add new shapes to the next generation
            next_gen.append(c1)
            next_gen.append(c2)

        # Update population and ranking
        cur_pop = next_gen
        ranking = rank(cur_pop, i+1)

        # Print the control points of the best solution in each generation
        print(f"Generation {i+1} best solution is:")
        print(ranking[0])

        # Plot the fitpoints and control points of the best solution every 10 generations
        # if (i+1)%10 == 0:
        #     fig, ax = plt.subplots()
        #     plt.title(f"Generation {i+1}")
        #     plot_fitpoints(ranking[0][1], show_points=True)
        #     plot_polygon(ax, airfoil_points, 'Airfoil')
        #     # Plot the control points of the original airfoil during the last generation
        #     if i+1 == num_generations:
        #         for s in range(len(splines_list1)): 
        #             plt.plot(splines_list1[s][:,0], splines_list1[s][:,1], 'o--')

        # if i == num_generations-1:
        #     # Create a formatted file containing the optimized control points in the current directory
        #     save_ctrlpts(ranking[0][1], i)