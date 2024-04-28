import multiprocessing 
import time 
import numpy as np

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

def multiprocessor():
    pass


# if __name__ == '__main__': 
#     fix_boundary('./base/airfoilOptTest1Clean/constant/polyMesh')
  
def squared(x): 
    time.sleep(5)
    print(x*x)
    return x * x 
   
if __name__ == '__main__': 
    pool = multiprocessing.Pool() 
    pool = multiprocessing.Pool(processes=4) 
    inputs = [0,1,2,3,4] 
    outputs = pool.map(squared, inputs) 
    print("Input: {}".format(inputs)) 
    print("Output: {}".format(outputs)) 