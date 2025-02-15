import sys

from parser import Parser

if __name__ == '__main__':

    p = Parser(*sys.argv[1:])
    p.run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
