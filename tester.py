import os

input = 'core0'

# os.chdir('./runtime/{}'.format(input))

# for file in os.listdir('./'):
#     if file != '0' and file != 'constant' and file != 'system' and file != 'Allclean' and file != 'Allrun':
#         os.system('rm -r ./{}'.format(file))

# print(len(os.listdir('./runtime')))
# print(os.getcwd())

# read cl/cd from coefficient.dat
with open('./coefficient.dat', 'r') as f:

    consider_csv = False
    coeff_csv = ''
    
    for line in f:
        if 'Cl' in line and 'Cd' in line:
            
            consider_csv = True

        if consider_csv:
            coeff_csv += line + '\n'


# now we need to parse the csv
import csv

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