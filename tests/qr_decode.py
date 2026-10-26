"""A minimal QR decoder for tests (Phase 14D): reads back the payload of an UNDAMAGED byte-mode QR code from its module matrix, so the
setup QR can be checked against the otpauth:// URI without a camera, a browser or a network.

It follows the QR specification (ISO/IEC 18004) independently of the encoder: format bits, function-pattern map, data unmasking, the
zigzag codeword order, block de-interleaving and byte-mode parsing. Only the standard's lookup tables (codewords per block, block counts,
raw module count, alignment positions) are taken from the vendored module, since they are data from the standard, not encoding logic.
No error correction is attempted: a matrix that is not exactly right fails to decode."""
from backend.vendor.qrcodegen import QrCode

_ECL_BY_FORMAT = {1: 0, 0: 1, 3: 2, 2: 3}             # format bits -> table row (LOW, MEDIUM, QUARTILE, HIGH)
_MASKS = (
    lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0, lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0, lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
)


def _function_map(size, version):
    fn = [[False] * size for _ in range(size)]

    def mark(x0, y0, w, h):
        for y in range(max(0, y0), min(size, y0 + h)):
            for x in range(max(0, x0), min(size, x0 + w)):
                fn[y][x] = True

    for x0, y0 in ((0, 0), (size - 8, 0), (0, size - 8)):  # finder patterns with separators
        mark(x0, y0, 8, 8)
    mark(6, 0, 1, size)                                    # timing patterns
    mark(0, 6, size, 1)
    positions = _alignment(version)
    for i, cx in enumerate(positions):
        for j, cy in enumerate(positions):
            if (i == 0 and j == 0) or (i == 0 and j == len(positions) - 1) or (i == len(positions) - 1 and j == 0):
                continue
            mark(cx - 2, cy - 2, 5, 5)
    mark(0, 8, 9, 1)                                       # format information (and the dark module)
    mark(8, 0, 1, 9)
    mark(size - 8, 8, 8, 1)
    mark(8, size - 8, 1, 8)
    if version >= 7:                                       # version information
        mark(size - 11, 0, 3, 6)
        mark(0, size - 11, 6, 3)
    return fn


def _alignment(version):
    if version == 1:
        return []
    num = version // 7 + 2
    step = (version * 8 + num * 3 + 5) // (num * 4 - 4) * 2
    result = [(version * 4 + 10) - i * step for i in range(num - 1)] + [6]
    return list(reversed(result))


def decode(qr):
    """`qr` is {"size": n, "modules": ["0101...", ...]}. Returns the decoded text."""
    size, rows = qr["size"], qr["modules"]
    dark = lambda x, y: rows[y][x] == "1"
    version = (size - 17) // 4
    assert 1 <= version <= 40 and size == version * 4 + 17

    bits = 0
    for i in range(6):
        bits |= dark(8, i) << i
    bits |= dark(8, 7) << 6
    bits |= dark(8, 8) << 7
    bits |= dark(7, 8) << 8
    for i in range(9, 15):
        bits |= dark(14 - i, 8) << i
    data5 = (bits ^ 0x5412) >> 10
    ecl_row, mask = _ECL_BY_FORMAT[data5 >> 3], _MASKS[data5 & 7]

    fn = _function_map(size, version)
    raw_codewords = QrCode._get_num_raw_data_modules(version) // 8
    stream = []
    for right in range(size - 1, 0, -2):
        if right <= 6:
            right -= 1
        for vert in range(size):
            for j in range(2):
                x = right - j
                upward = ((right + 1) & 2) == 0
                y = size - 1 - vert if upward else vert
                if not fn[y][x] and len(stream) < raw_codewords * 8:
                    stream.append(int(dark(x, y)) ^ int(mask(x, y)))
    codewords = [int("".join(map(str, stream[i:i + 8])), 2) for i in range(0, raw_codewords * 8, 8)]

    num_blocks = QrCode._NUM_ERROR_CORRECTION_BLOCKS[ecl_row][version]
    ecc_len = QrCode._ECC_CODEWORDS_PER_BLOCK[ecl_row][version]
    short_count = num_blocks - raw_codewords % num_blocks
    short_len = raw_codewords // num_blocks
    lengths = [short_len - ecc_len + (0 if b < short_count else 1) for b in range(num_blocks)]
    blocks = [[] for _ in range(num_blocks)]
    k = 0
    for i in range(max(lengths)):                          # data codewords are interleaved block by block
        for b in range(num_blocks):
            if i < lengths[b]:
                blocks[b].append(codewords[k])
                k += 1
    data = [c for block in blocks for c in block]

    bitstr = "".join(f"{c:08b}" for c in data)
    assert bitstr[:4] == "0100", "not a byte-mode segment"
    count_bits = 8 if version <= 9 else 16
    n = int(bitstr[4:4 + count_bits], 2)
    start = 4 + count_bits
    payload = bytes(int(bitstr[start + 8 * i:start + 8 * i + 8], 2) for i in range(n))
    return payload.decode("utf-8")
