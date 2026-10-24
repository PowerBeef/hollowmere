"""GBA BIOS-compatible LZ77 (type 0x10) compressor.
Matches always use displacement >= 2 so output is safe for the VRAM
(16-bit write) decompressor as well as the WRAM one."""


def compress(data: bytes) -> bytes:
    data = bytes(data)
    n = len(data)
    out = bytearray()
    out += bytes([0x10, n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF])
    # hash chains for speed
    head = {}
    prev = [-1] * n
    i = 0

    def insert(pos):
        if pos + 2 < n:
            key = data[pos:pos + 3]
            prev[pos] = head.get(key, -1)
            head[key] = pos

    while i < n:
        flag_pos = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if i >= n:
                break
            best_len, best_disp = 0, 0
            if i + 2 < n:
                key = data[i:i + 3]
                cand = head.get(key, -1)
                tries = 0
                maxlen = min(18, n - i)
                while cand >= 0 and tries < 256:
                    disp = i - cand
                    if disp > 4096:
                        break
                    if disp >= 2:
                        l = 0
                        while l < maxlen and data[cand + l] == data[i + l]:
                            l += 1
                        if l > best_len:
                            best_len, best_disp = l, disp
                            if l == maxlen:
                                break
                    cand = prev[cand]
                    tries += 1
            if best_len >= 3:
                flags |= 0x80 >> bit
                d = best_disp - 1
                out.append(((best_len - 3) << 4) | (d >> 8))
                out.append(d & 0xFF)
                for k in range(best_len):
                    insert(i + k)
                i += best_len
            else:
                out.append(data[i])
                insert(i)
                i += 1
        out[flag_pos] = flags
    while len(out) % 4:
        out.append(0)
    return bytes(out)


def decompress(comp: bytes) -> bytes:
    n = comp[1] | (comp[2] << 8) | (comp[3] << 16)
    out = bytearray()
    p = 4
    while len(out) < n:
        flags = comp[p]; p += 1
        for bit in range(8):
            if len(out) >= n:
                break
            if flags & (0x80 >> bit):
                b1, b2 = comp[p], comp[p + 1]; p += 2
                l = (b1 >> 4) + 3
                d = ((b1 & 0xF) << 8 | b2) + 1
                for _ in range(l):
                    out.append(out[-d])
            else:
                out.append(comp[p]); p += 1
    return bytes(out[:n])


if __name__ == '__main__':
    import os
    for t in [b'', b'a', b'abcabcabcabcabc' * 50, os.urandom(1000), bytes(5000)]:
        c = compress(t)
        assert decompress(c) == t, t[:20]
    print('lz77 ok')
