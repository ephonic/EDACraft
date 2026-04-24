import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from tests.test_montgomery_mult_384 import modinv

def ref_standard(X, Y, M, n=384):
    R = 1 << n
    T = X * Y
    M_prime = (-modinv(M, R)) % R
    q = (T * M_prime) & (R - 1)
    Z = (T + q * M) >> n
    if Z >= M:
        Z -= M
    return Z

def ref_sos_hardware(X, Y, M, n=384):
    """Reference matching hardware: 3 iterations of 128-bit SOS."""
    w = 128
    T = X * Y
    Mp = (-modinv(M, 1 << w)) % (1 << w)
    
    # Split T into words
    k = n // w
    T_words = [(T >> (i * w)) & ((1 << w) - 1) for i in range(k)]
    M_words = [(M >> (i * w)) & ((1 << w) - 1) for i in range(k)]
    
    Z = list(T_words) + [0] * (k + 1)  # extra word for overflow
    
    for i in range(k):
        q = (Z[i] * Mp) & ((1 << w) - 1)
        carry = 0
        for j in range(k):
            prod = q * M_words[j] + Z[i + j] + carry
            Z[i + j] = prod & ((1 << w) - 1)
            carry = prod >> w
        Z[i + k] += carry
    
    # Result is Z[k:2k]
    result = 0
    for i in range(k):
        result |= Z[k + i] << (i * w)
    
    if result >= M:
        result -= M
    return result

# Reproduce the failing random vector
random = __import__('random')
random.seed(2024)
M = random.getrandbits(384) | 1
M |= (1 << 383)
X = random.randint(0, M - 1)
Y = random.randint(0, M - 1)

std = ref_standard(X, Y, M)
sos = ref_sos_hardware(X, Y, M)

print("M =", hex(M))
print("X =", hex(X))
print("Y =", hex(Y))
print("standard =", hex(std))
print("sos      =", hex(sos))
print("match    =", std == sos)

if std != sos:
    diff = (std - sos) % (1 << 384)
    print("diff     =", hex(diff))
