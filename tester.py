import os

input = 'core0'

# os.chdir('./runtime/{}'.format(input))

# for file in os.listdir('./'):
#     if file != '0' and file != 'constant' and file != 'system' and file != 'Allclean' and file != 'Allrun':
#         os.system('rm -r ./{}'.format(file))

print(len(os.listdir('./runtime')))