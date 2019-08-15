import sys
sys.path.append("../cachesim_playground")
from analyser import Analyser, ArrayWrapper
from cachesim import CacheConfig, extract_index, extract_block_offset, extract_tag
from random import sample, randint
from math import log2
import re


def generate(data):
####################################################################################
# CACHE CONFIGURATION
    # Associativity, ranged from 1way to 4way
    asso = 2**randint(0, 2)
    # Cache size, ranged from 1KB to 32KB
    # if associativity = 1, the cache size cannot be < 16KB; otherwise, part(b) will fail
    size = 2**randint(0 if asso > 1 else 4, 5) * 1024
    # Block size, ranged from 16B to 64B
    bsize = 2**randint(4, 6)
    # The number of digits of addresses in hexadecimal
    hexdigits = randint(6, 8)
    # Address length, ranged from 24bit to 32bit
    addrbits = 4 * hexdigits
####################################################################################
# GENERATE ADDRESSES
    # helper function to generates fixed-width binary strings with the given range
    def _random_bits_(numBits): return format(
        randint(0, (1 << numBits) - 1), '0%db' % numBits)

    # create the given cache configuration to help extract bits
    cache_config = CacheConfig(size, bsize, asso, addrbits)
    numIndexBits = cache_config.get_num_index_bits()
    numOffsetBits = cache_config.get_num_block_offset_bits()
    numTagBits = cache_config.get_num_tag_bits()
    # randomly generate index bits and offset bits as fixed-width binary strings
    indexBits = _random_bits_(numIndexBits)
    # make sure the offset is divisible by 8 and every address has the same offset
    offsetBits = '0' * numOffsetBits if numOffsetBits <= 3 else _random_bits_(
        numOffsetBits - 3)+'0'*3
    # randomly generate tag bits to produce addresses
    # we must make sure three addresses have the same offset bits
    tagBits = _random_bits_(numTagBits)
    rndAddr1 = tagBits + indexBits + offsetBits
    rndAddr1 = '0x' + format(int(rndAddr1, 2), '0%dX' % hexdigits)
    # Array B starts at the same index bits as Array A
    tagBits = _random_bits_(numTagBits)
    rndAddr2 = tagBits + indexBits + offsetBits
    rndAddr2 = '0x' + format(int(rndAddr2, 2), '0%dX' % hexdigits)
    # Array C also starts at the same index bits as Array A
    tagBits = _random_bits_(numTagBits)
    rndAddr3 = tagBits + indexBits + offsetBits
    rndAddr3 = '0x' + format(int(rndAddr3, 2), '0%dX' % hexdigits)

    # The beginning addresses for arrays
    # !! MODIFY THE VARIABLE NAMES IF CHANGING C CODE !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    addresses = {"A": rndAddr1,
                 "B": rndAddr2,
                 "C": rndAddr3}
####################################################################################
# C CODE
    # constant N in C code
    N = 16
    # constant M in C code
    M = 1024
    # the number of iterations needed in part (b)
    # after this iteration, analyser pauses and checks which elements are in the cache
    itr = 1
    # randomly choose two types
    types = sample(('int', 'double', 'float', 'long long', 'short', 'char'), 2)
    data["params"]["type0"] = types[0]
    data["params"]["type1"] = types[1]
    # the given C code
    c_code = '''
#define M %d
#define N %d
%s A[N][M], B[M], C[N]; // A and B filled in elsewhere
for (int i = 0; i < N; ++i) { // Loop 1
    C[i] = 0;
    for (int j = 0; j < M; ++j) { // Loop 2
        C[i] += A[i][j] * B[j];
    }
}''' % (M, N, types[0])

    # the following are corresbonding parameters in the question.html
    data["params"]["size"] = size//1024
    data["params"]["asso"] = asso
    data["params"]["bsize"] = bsize
    data["params"]["addrbits"] = addrbits
    data["params"]["code"] = c_code
    for name in addresses:
        data["params"]["addr" + name] = addresses[name]
####################################################################################
# PART B
    # initialize the analyser with given configuration
    analyser = Analyser(size, bsize, asso, addrbits)
    # run the given C code, stop at the given iteration and return variables
    _c_code = c_code.replace("for (int i = 0; i < N; ++i)", "for (int i = 0; i < %s; ++i)" % itr)
    varList = analyser.runcode(_c_code, addresses)
    # generate random indices for arrays and give the correct answers
    for array in varList:
        # get the current array name
        name = array.get_varname()
        # get dimensions of the array
        dim = array.get_dimensions()
        # use the last dimension as rng
        rng = dim[-1]
        # generate four indices ranged from 0 to rng
        indices = sample(range(rng), 4)
        # valid flag to make sure there must be at least a correct answer
        flag = False
        # give the correct answer for each index
        for i, index in enumerate(indices):
            # fill in the placeholder of indices in part(b)
            data["params"]["index"+name+str(i)] = str(index)
            # generate index list
            # used to deal with two-dim arrays and one-dim arrays and separately
            # !! MODIFY HERE IF CHANGING C CODE !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            idxList = [0, index] if len(dim) == 2 else [index]
            # check whether the element at given index is in cache or not
            isInCache = array.check_element_in_cache(idxList)
            # fill in the placeholder of the correct answers in part(b)
            data["params"]["checkbox"+name+ str(i)] = "true" if isInCache else "false"
            # update flag
            flag = flag or isInCache
        # check whether there is no answer
        data["params"]["checkbox"+name+"NA"] = "true" if not flag else "false"
####################################################################################
# PART A & C
    # reset analyser for re-running code
    analyser.reset()
    # run the given C code till it halts
    analyser.runcode(c_code, addresses)
    # get back the log
    answer = analyser.get_log()
    # get the correct answers for first several accesses in part (a)
    for i in range(6):
        data["correct_answers"]["addr" + str(i)] = format(answer[i]['address'], '0%dX' % hexdigits)
        data["params"]["hit" + str(i)] = "true" if answer[i]['hit'] else "false"
        data["params"]["miss" + str(i)] = "false" if answer[i]['hit'] else "true"
    # get the correct answers for the number of accesses and misses in part (c)
    for name in addresses:
        data["correct_answers"]["num_accesses" + name] = analyser.get_num_accesses(name)
        data["correct_answers"]["num_misses" + name] = analyser.get_num_misses(name)
    # get total number of accesses and misses for testing purposes
    
####################################################################################
# PART D
    # replace types in C code
    c_code = re.sub("(?<=\n)%s " % types[0], "%s " % types[1], c_code)
    # reset analyser for re-running code
    analyser.reset()
    # re-run the modified code
    analyser.runcode(c_code, addresses)
    # get the correct answer for the new number of misses
    data["correct_answers"]["new_num_misses"] = analyser.get_num_misses()
####################################################################################
    return data
