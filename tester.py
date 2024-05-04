import os
import csv

input = 'core0'

# os.chdir('./runtime/{}'.format(input))

# for file in os.listdir('./'):
#     if file != '0' and file != 'constant' and file != 'system' and file != 'Allclean' and file != 'Allrun':
#         os.system('rm -r ./{}'.format(file))

# print(len(os.listdir('./runtime')))
# print(os.getcwd())

# read cl/cd from coefficient.dat
# with open('./coefficient.dat', 'r') as f:

#     consider_csv = False
#     coeff_csv = ''
    
#     for line in f:
#         if 'Cl' in line and 'Cd' in line:
            
#             consider_csv = True

#         if consider_csv:
#             coeff_csv += line + '\n'


# # now we need to parse the csv
# import csv

# reader = csv.reader(coeff_csv.split('\n'), delimiter='\t')    
# print(reader)
# cd = 2
# cl = 3
# # look at first row to see where Cd and Cl are
# for idx, row in enumerate(next(reader)):
#     row = row.strip() 
#     if row == 'Cd':
#         cd = idx
#     if row == 'Cl':
#         cl = idx
# # go to last row to get the values
# for row in reader:
#     if row:

#         # in case tab delimiters didn't parse correctly
#         if len(row) < 4:
#             row = row[0].split(' ')
#             row = [x for x in row if x]

#         # store latest cl cd
#         cd_val = row[cd]
#         cl_val = row[cl]

# print(cd_val, cl_val)

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import BSpline
import scipy.interpolate as si
import json
import shapely


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

def plot_fitpoints(splines, show_points=True):
    for s in range(len(splines)): 
        if show_points == True:
            plt.plot(splines[s][:,0], splines[s][:,1], 'o--', label=f'Spline {s+1}')
        p = scipy_bspline(splines[s], n=50, degree=5, periodic=False)
        x,y = p.T
        # Setting equal aspect ratio for both axes to avoid distortion
        plt.axis('equal')
        plt.plot(x,y,)
    plt.show()
        

def coords_to_splines(xC, yC, zC, degree = 5):

    splines = []
    cur_spline = []

    for idx, elem in enumerate(xC):
        cur_spline.append([float(xC[idx]), float(yC[idx])])

        if idx % (degree + 1) == degree:
            splines.append(np.array(cur_spline))
            cur_spline = []

    return splines

xC = [1.012481157187128, 0.9618595204193467, 0.8033302548395505, 0.5603173590524105, 0.3873763032702343, 0.18470095716718143, 0.18470095716718143, 0.10543225447641287, -0.08162858850221558, -0.065728163987333, 0.1094218594140584, 0.17504135078832145, 0.17504135078832145, 0.3864419131074707, 0.5737925886111878, 0.7983476721422594, 0.9668382290966343, 1.012481157187128]
yC = [0.001983070787701114, -0.006154532122824076, -0.025227789198357997, -0.05010568700234853, -0.0716263707319749, -0.055034843105266455, -0.055034843105266455, -0.04969315952636594, -0.030012471290268995, 0.043182505504219024, 0.04227387899379136, 0.05132896003888626, 0.05132896003888626, 0.07016395581405857, 0.049073689078245435, 0.03046499503696143, 0.006176514963667031, 0.001983070787701114]
zC = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

splines = coords_to_splines(xC, yC, zC)

splines = [[[1.00000005, 0.0], [0.9742102063184167, -0.011702337924488276], [0.8080025270918115, -0.04051507809091624], [0.5792874285201217, -0.04830524443080556], [0.39263554760260727, -0.06900860826086848], [0.17905778, -0.05614943]], [[0.17905778, -0.05614943], [0.1096921724210349, -0.05112066908199496], [-0.08278311744423719, -0.03984609707084383], [-0.08142668413463941, 0.039083022071179425], [0.10268049352591876, 0.05249133127574103], [0.17905778, 0.05614943]], [[0.17905778, 0.05614943], [0.39392021477798606, 0.06171724887648374], [0.5649224931152602, 0.042962173411279184], [0.8064189367646522, 0.028571339173103713], [0.9559271595298963, 0.004722399494827325], [1.00000005, 0.0]]]

points = get_fitpoints(splines)
plot_fitpoints(splines, show_points=True)

