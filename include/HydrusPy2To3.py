import os

from . import HydrusConstants as HC


def do_2to3_test():

    bad_filenames = ['python27.dll', 'lz4._version.so']

    for bad_filename in bad_filenames:

        path = os.path.join(HC.BASE_DIR, bad_filename)

        if os.path.exists(path):

            message = 'It looks like you still have some Python 2 files in your install directory! Hydrus is now Python 3 and needs a clean install. Please check the v335 release post for more information! The program will now exit!'

            print(message)

            raise Exception('Client needs a clean install!')
