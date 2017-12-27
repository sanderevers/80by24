from run80by24.common import id_generator
import sys

if __name__=='__main__':
    # make it work for one argument with spaces and for multiple arguments
    words = []
    for arg in sys.argv[1:]:
        words.extend(arg.split())
    hash = id_generator.id_hash(words)
    print(hash)


