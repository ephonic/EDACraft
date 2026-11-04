#!/usr/bin/env python3
"""DWF1 research prototype: lossless digital VCD events, indexed entropy blocks.

Not a stable interchange format or a simulator dump implementation. Zstandard uses Python 3.14 compression.zstd or a system libzstd fallback;
raw and DEFLATE work on Python 3.10+.
"""
import argparse
import bisect
import ctypes
import ctypes.util
import json
import os
import struct
import zlib
from pathlib import Path

try:
    from compression import zstd
except ImportError:
    zstd = None


def _system_zstd():
    """Single-frame libzstd backend for Python versions without compression.zstd."""
    name = ctypes.util.find_library('zstd')
    if not name:
        return None
    try:
        lib = ctypes.CDLL(name)
    except OSError:
        return None
    size = ctypes.c_size_t
    lib.ZSTD_compressBound.argtypes = [size]
    lib.ZSTD_compressBound.restype = size
    lib.ZSTD_compress.argtypes = [ctypes.c_void_p, size, ctypes.c_void_p, size, ctypes.c_int]
    lib.ZSTD_compress.restype = size
    lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, size, ctypes.c_void_p, size]
    lib.ZSTD_decompress.restype = size
    lib.ZSTD_findFrameCompressedSize.argtypes = [ctypes.c_void_p, size]
    lib.ZSTD_findFrameCompressedSize.restype = size
    lib.ZSTD_isError.argtypes = [size]
    lib.ZSTD_isError.restype = ctypes.c_uint

    class Decoder:
        eof = False
        unused_data = b''

        def decompress(self, data, max_length):
            if lib.ZSTD_findFrameCompressedSize(data, len(data)) != len(data):
                raise ValueError('invalid single Zstandard frame')
            output = ctypes.create_string_buffer(max_length)
            n = lib.ZSTD_decompress(output, max_length, data, len(data))
            if lib.ZSTD_isError(n):
                raise ValueError('Zstandard decoding failed or exceeds output limit')
            self.eof = True
            return output.raw[:n]

    class Backend:
        ZstdDecompressor = Decoder

        @staticmethod
        def compress(data, level=3):
            capacity = lib.ZSTD_compressBound(len(data))
            if lib.ZSTD_isError(capacity):
                raise ValueError('Zstandard compression bound failed')
            output = ctypes.create_string_buffer(capacity)
            n = lib.ZSTD_compress(output, capacity, data, len(data), level)
            if lib.ZSTD_isError(n):
                raise ValueError('Zstandard encoding failed')
            return output.raw[:n]

    return Backend()


if zstd is None:
    zstd = _system_zstd()

MAGIC = b'DWF1P001'
END = b'DWFEND01'
RECORD = struct.Struct('<4sB3xIII')  # tag, codec, raw bytes, stored bytes, CRC32
FOOTER = struct.Struct('<Q8s')
LIMIT = 64 * 1024 * 1024
MAX_BITS = 1024 * 1024
MAX_U64 = (1 << 64) - 1
CODECS = {'raw': 0, 'zlib': 1, 'zstd': 2}


def uint(n):
    if not 0 <= n <= MAX_U64:
        raise ValueError('integer outside uint64')
    out = bytearray()
    while n >= 128:
        out.append((n & 127) | 128)
        n >>= 7
    out.append(n)
    return bytes(out)


class Cursor:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, size):
        if size < 0 or size > len(self.data) - self.pos:
            raise ValueError('truncated block')
        out = self.data[self.pos:self.pos + size]
        self.pos += size
        return out

    def integer(self):
        n = 0
        for i in range(10):
            b = self.take(1)[0]
            if i == 9 and b > 1:
                raise ValueError('invalid uint64 varint')
            n |= (b & 127) << (7 * i)
            if b < 128:
                if i and b == 0:
                    raise ValueError('noncanonical varint')
                return n
        raise ValueError('invalid varint')

    def done(self):
        if self.pos != len(self.data):
            raise ValueError('trailing block bytes')


def json_bytes(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode()


def _read_exact(f, size):
    data = f.read(size)
    if len(data) != size:
        raise ValueError('truncated file')
    return data


def write_record(f, tag, raw, codec):
    if len(raw) > LIMIT:
        raise ValueError('record exceeds 64 MiB limit')
    packed = raw
    used = 0
    if codec == 'zlib':
        packed, used = zlib.compress(raw, 3), 1
    elif codec == 'zstd':
        if zstd is None:
            raise ValueError('zstd requires Python 3.14 compression.zstd or libzstd')
        packed, used = zstd.compress(raw, level=3), 2
    elif codec != 'raw':
        raise ValueError('unknown codec')
    if len(packed) >= len(raw):
        packed, used = raw, 0
    offset = f.tell()
    f.write(RECORD.pack(tag, used, len(raw), len(packed), zlib.crc32(raw)))
    f.write(packed)
    return offset


def read_record(f, expected_tag, end_limit):
    if f.tell() + RECORD.size > end_limit:
        raise ValueError('record outside section')
    tag, codec, raw_len, stored_len, crc = RECORD.unpack(_read_exact(f, RECORD.size))
    if tag != expected_tag or max(raw_len, stored_len) > LIMIT:
        raise ValueError('invalid record header')
    if f.tell() + stored_len > end_limit:
        raise ValueError('record outside section')
    packed = _read_exact(f, stored_len)
    if codec == 0:
        raw = packed
    elif codec == 1:
        d = zlib.decompressobj()
        raw = d.decompress(packed, raw_len + 1)
        if not d.eof or d.unused_data or d.unconsumed_tail:
            raise ValueError('invalid DEFLATE frame')
    elif codec == 2:
        if zstd is None:
            raise ValueError('zstd requires Python 3.14 compression.zstd or libzstd')
        d = zstd.ZstdDecompressor()
        try:
            raw = d.decompress(packed, max_length=raw_len + 1)
        except (ValueError, getattr(zstd, 'ZstdError', ValueError)) as error:
            raise ValueError('invalid Zstandard frame') from error
        if not d.eof or d.unused_data:
            raise ValueError('invalid Zstandard frame')
    else:
        raise ValueError('unknown block codec')
    if len(raw) != raw_len or zlib.crc32(raw) != crc:
        raise ValueError('record length/checksum mismatch')
    return raw


def planes(bits, width):
    bits = bits.lower()
    if not bits or len(bits) > width or set(bits) - set('01xz'):
        raise ValueError('invalid digital value or width')
    # VCD abbreviation: x/z extends itself; a binary digit extends with zero.
    bits = bits.rjust(width, bits[0] if bits[0] in 'xz' else '0')
    return (int(bits.translate(str.maketrans('xz', '10')), 2),
            int(bits.translate(str.maketrans('01xz', '0011')), 2))


def bit_string(value, width):
    a, b = value
    return ''.join('01zx'[((a >> i) & 1) + 2 * ((b >> i) & 1)]
                   for i in range(width - 1, -1, -1))


def encode_value(value, previous, width):
    if value is None:
        return b'\x08'  # unseen (checkpoint only)
    a, b = value
    mask, size = (1 << width) - 1, (width + 7) // 8
    for mode, pair in enumerate([(0, 0), (mask, 0), (mask, mask), (0, mask)]):
        if value == pair:
            return bytes([mode])
    full = bytes([4]) + a.to_bytes(size, 'little')
    if b:
        full = bytes([5]) + a.to_bytes(size, 'little') + b.to_bytes(size, 'little')
    if previous is not None:
        # Trim high zero bytes of XOR bit planes; no change is two zero lengths.
        delta = bytearray([6])
        for x, y in zip(value, previous):
            x ^= y
            packed = x.to_bytes((x.bit_length() + 7) // 8, 'little')
            delta += uint(len(packed)) + packed
        if len(delta) < len(full):
            return bytes(delta)
    return full


def decode_value(c, previous, width, checkpoint=False):
    mode = c.take(1)[0]
    mask, size = (1 << width) - 1, (width + 7) // 8
    if mode < 4:
        return [(0, 0), (mask, 0), (mask, mask), (0, mask)][mode]
    if mode == 8 and checkpoint:
        return None
    if mode in (4, 5):
        value = (int.from_bytes(c.take(size), 'little'),
                 int.from_bytes(c.take(size), 'little') if mode == 5 else 0)
    elif mode == 6 and previous is not None and not checkpoint:
        delta = []
        for _ in range(2):
            length = c.integer()
            if length > size:
                raise ValueError('XOR plane outside signal width')
            delta.append(int.from_bytes(c.take(length), 'little'))
        value = tuple(x ^ y for x, y in zip(previous, delta))
    else:
        raise ValueError('invalid value mode')
    if any(v > mask for v in value):
        raise ValueError('nonzero padding bits')
    return value


def tokens(f):
    # Streaming line reader; reject pathological single lines before tokenizing.
    while line := f.readline(LIMIT + 1):
        if len(line) > LIMIT:
            raise ValueError('VCD line exceeds limit')
        yield from line.split()


def directive(first, stream):
    parts = [first]
    for token in stream:
        parts.append(token)
        if token == '$end':
            return parts
    raise ValueError('unterminated VCD directive')


def read_vcd_header(f):
    stream = iter(tokens(f))
    header, signals, ids, scope = [], [], {}, []
    for first in stream:
        if not first.startswith('$'):
            raise ValueError('expected VCD header directive')
        parts = directive(first, stream)
        header.append(parts)
        if first == '$scope':
            if len(parts) != 4:
                raise ValueError('invalid scope')
            scope.append(parts[2])
        elif first == '$upscope':
            if len(parts) != 2 or not scope:
                raise ValueError('invalid upscope')
            scope.pop()
        elif first == '$var':
            if len(parts) < 6 or parts[1] in ('string', 'event'):
                raise ValueError('only persistent digital VCD variables supported')
            width, code = int(parts[2]), parts[3]
            if not 1 <= width <= MAX_BITS:
                raise ValueError('signal width outside prototype limit')
            alias = {'scope': list(scope), 'declaration': parts[1:-1]}
            if code in ids:
                if signals[ids[code]]['width'] != width:
                    raise ValueError('alias width mismatch')
                signals[ids[code]]['aliases'].append(alias)
            else:
                ids[code] = len(signals)
                signals.append({'code': code, 'width': width, 'aliases': [alias]})
                if parts[1] in ('real', 'realtime'):
                    if width not in (32, 64):
                        raise ValueError('real waveform width must be 32 or 64')
                    signals[-1]['type'] = 'real'
        elif first == '$enddefinitions':
            if scope:
                raise ValueError('unclosed scope')
            return {'schema': 'dsim.wave.prototype.v2' if any(s.get('type') == 'real' for s in signals) else 'dsim.wave.prototype.v1', 'header': header,
                    'signals': signals}, stream
        elif first not in ('$date', '$version', '$timescale', '$comment'):
            raise ValueError('unsupported VCD header directive: ' + first)
    raise ValueError('missing enddefinitions')


def vcd_events(stream, meta):
    ids = {s['code']: i for i, s in enumerate(meta['signals'])}
    time = 0
    for token in stream:
        if token.startswith('#'):
            n = int(token[1:])
            if not time <= n <= MAX_U64:
                raise ValueError('nonmonotonic or overflowing VCD time')
            time = n
            yield time, 'time', None
        elif token in ('$dumpvars', '$dumpon', '$dumpoff', '$dumpall', '$end'):
            yield time, 'control', [token]
        elif token == '$comment':
            yield time, 'control', directive(token, stream)
        else:
            if token[0] in 'rR':
                code = next(stream, '')
                if code not in ids or meta['signals'][ids[code]].get('type') != 'real':
                    raise ValueError('invalid real declaration')
                ident = ids[code]
                sig = meta['signals'][ident]
                raw = struct.pack('<f' if sig['width'] == 32 else '<d', float(token[1:]))
                yield time, 'value', (ident, (int.from_bytes(raw, 'little'), 0))
                continue
            if token[0] in '01xXzZ':
                code, bits = token[1:], token[0]
                if code not in ids or meta['signals'][ids[code]]['width'] != 1:
                    raise ValueError('invalid scalar declaration')
            elif token[0] in 'bB':
                bits, code = token[1:], next(stream, '')
            else:
                raise ValueError('unsupported VCD event: ' + token)
            if code not in ids:
                raise ValueError('undeclared VCD signal')
            ident = ids[code]
            yield time, 'value', (ident, planes(bits, meta['signals'][ident]['width']))


class Writer:
    def __init__(self, f, meta, codec='zstd', block_events=16384):
        if codec not in CODECS or not 1 <= block_events <= 1000000:
            raise ValueError('invalid writer configuration')
        self.f, self.meta, self.codec, self.block_events = f, meta, codec, block_events
        self.state = [None] * len(meta['signals'])
        self.time, self.index, self.body, self.count = 0, [], bytearray(), 0
        f.write(MAGIC)
        write_record(f, b'META', json_bytes(meta), codec)
        self._checkpoint()

    def _checkpoint(self):
        self.start = self.time
        self.checkpoint = uint(self.time) + uint(len(self.state))
        self.checkpoint += b''.join(encode_value(v, None, s['width'])
                                    for v, s in zip(self.state, self.meta['signals']))
        if len(self.checkpoint) > LIMIT // 2:
            raise ValueError('checkpoint exceeds prototype limit')

    def append(self, event):
        time, kind, payload = event
        if not self.time <= time <= MAX_U64:
            raise ValueError('nonmonotonic event time')
        if time != self.time and kind != 'time':
            self.append((time, 'time', None))
        if kind == 'time':
            encoded = b'\x00' + uint(time - self.time)
        elif kind == 'value':
            ident, value = payload
            if not 0 <= ident < len(self.state):
                raise ValueError('invalid signal ID')
            mask = (1 << self.meta['signals'][ident]['width']) - 1
            if value is None or len(value) != 2 or any(type(v) is not int or not 0 <= v <= mask for v in value):
                raise ValueError('value outside signal width')
            encoded = b'\x01' + uint(ident) + encode_value(value, self.state[ident], self.meta['signals'][ident]['width'])
        elif kind == 'control':
            raw = json_bytes(payload)
            encoded = b'\x02' + uint(len(raw)) + raw
        else:
            raise ValueError('unknown event kind')
        if len(self.body) + len(encoded) + len(self.checkpoint) + 20 > LIMIT:
            self.flush()
            # Re-encode XOR relative to the unchanged state after block flush.
        self.body += encoded
        self.time = time
        if kind == 'value':
            self.state[payload[0]] = payload[1]
        self.count += 1
        if self.count >= self.block_events:
            self.flush()

    def flush(self):
        if not self.count:
            return
        raw = self.checkpoint + uint(self.count) + self.body
        offset = write_record(self.f, b'BLK1', raw, self.codec)
        self.index.append([self.start, self.time, offset, self.f.tell(), self.count])
        self.body, self.count = bytearray(), 0
        self._checkpoint()

    def close(self):
        self.flush()
        offset = write_record(self.f, b'INDX', json_bytes(self.index), self.codec)
        self.f.write(FOOTER.pack(offset, END))


def _read_metadata(f, end_limit):
    meta = json.loads(read_record(f, b'META', end_limit))
    if not isinstance(meta, dict) or meta.get('schema') not in ('dsim.wave.prototype.v1', 'dsim.wave.prototype.v2'):
        raise ValueError('unsupported metadata schema')
    sigs = meta.get('signals')
    if (not isinstance(sigs, list) or any(not isinstance(s, dict)
            or not isinstance(s.get('code'), str) or not s['code']
            or type(s.get('width')) is not int or not 1 <= s['width'] <= MAX_BITS for s in sigs)):
        raise ValueError('invalid signal dictionary')
    if len({s['code'] for s in sigs}) != len(sigs):
        raise ValueError('invalid signal dictionary')
    if any(s.get('type') not in (None, 'real') or
           (s.get('type') == 'real' and s['width'] not in (32, 64)) for s in sigs):
        raise ValueError('invalid signal type')
    if (not isinstance(meta.get('header'), list) or any(not isinstance(row, list)
            or not all(isinstance(token, str) for token in row) for row in meta['header'])):
        raise ValueError('invalid declaration header')
    return meta


def _decode_block(meta, raw):
    c = Cursor(raw)
    time, n = c.integer(), c.integer()
    first = time
    if n != len(meta['signals']):
        raise ValueError('checkpoint dictionary mismatch')
    state = [decode_value(c, None, s['width'], True) for s in meta['signals']]
    before = list(state)
    count = c.integer()
    if not 1 <= count <= 1000000:
        raise ValueError('invalid event count')
    events = []
    for _ in range(count):
        mode = c.take(1)[0]
        if mode == 0:
            time += c.integer()
            if time > MAX_U64:
                raise ValueError('overflowing timestamp')
            events.append((time, 'time', None))
        elif mode == 1:
            ident = c.integer()
            if ident >= n:
                raise ValueError('invalid signal ID')
            value = decode_value(c, state[ident], meta['signals'][ident]['width'])
            state[ident] = value
            events.append((time, 'value', (ident, value)))
        elif mode == 2:
            control = json.loads(c.take(c.integer()))
            if (not isinstance(control, list) or not control
                    or not all(isinstance(t, str) for t in control)
                    or (control[0] not in ('$dumpvars', '$dumpon', '$dumpoff', '$dumpall', '$end')
                        and not (control[0] == '$comment' and control[-1] == '$end'))):
                raise ValueError('invalid control record')
            events.append((time, 'control', control))
        else:
            raise ValueError('unknown event opcode')
    c.done()
    return first, time, count, before, events, state


class Reader:
    def __init__(self, f):
        self.f, self.decoded_blocks = f, 0
        f.seek(0, 2)
        self.size = f.tell()
        if self.size < len(MAGIC) + FOOTER.size:
            raise ValueError('incomplete DWF file')
        f.seek(-FOOTER.size, 2)
        self.index_offset, end = FOOTER.unpack(_read_exact(f, FOOTER.size))
        if end != END or not len(MAGIC) <= self.index_offset < self.size - FOOTER.size:
            raise ValueError('missing/invalid finalized index')
        f.seek(0)
        if _read_exact(f, len(MAGIC)) != MAGIC:
            raise ValueError('unsupported DWF version')
        self.meta = _read_metadata(f, self.index_offset)
        blocks_start = f.tell()
        f.seek(self.index_offset)
        self.index = json.loads(read_record(f, b'INDX', self.size - FOOTER.size))
        if not isinstance(self.index, list):
            raise ValueError('invalid block index')
        if f.tell() != self.size - FOOTER.size:
            raise ValueError('trailing index bytes')
        offset, time = blocks_start, 0
        for row in self.index:
            if (not isinstance(row, list) or len(row) != 5 or any(type(x) is not int for x in row)
                    or row[0] != time or not 0 <= row[0] <= row[1] <= MAX_U64
                    or row[2] != offset or not offset < row[3] <= self.index_offset
                    or not 1 <= row[4] <= 1000000):
                raise ValueError('invalid block index')
            time, offset = row[1], row[3]
        if offset != self.index_offset:
            raise ValueError('unindexed data')
        self.ends = [r[1] for r in self.index]

    def block(self, i):
        first, last, offset, end, count = self.index[i]
        self.f.seek(offset)
        raw = read_record(self.f, b'BLK1', end)
        if self.f.tell() != end:
            raise ValueError('block end mismatch')
        self.decoded_blocks += 1
        actual_first, actual_last, actual_count, before, events, state = _decode_block(self.meta, raw)
        if (actual_first, actual_last, actual_count) != (first, last, count):
            raise ValueError('block time/count mismatch')
        return before, events, state

    def events(self):
        state = [None] * len(self.meta['signals'])
        for i in range(len(self.index)):
            before, events, after = self.block(i)
            if state != before:
                raise ValueError('checkpoint continuity mismatch')
            yield from events
            state = after

    def window(self, start, end):
        """State immediately before start and all events in inclusive [start,end]."""
        if not 0 <= start <= end <= MAX_U64:
            raise ValueError('invalid time interval')
        if not self.index:
            return [None] * len(self.meta['signals']), []
        i = min(bisect.bisect_left(self.ends, start), len(self.index) - 1)
        state, selected = None, []
        while i < len(self.index) and self.index[i][0] <= end:
            before, events, after = self.block(i)
            if state is None:
                state = before
            for event in events:
                time, kind, payload = event
                if time < start:
                    if kind == 'value':
                        state[payload[0]] = payload[1]
                elif time <= end:
                    selected.append(event)
            i += 1
        return state, selected


def recover(input_path, output_path):
    """Rebuild an index over a contiguous, validated prefix; never skip blocks.

    An incomplete final record or damaged/missing final index can be removed.
    A complete bad data block, including a bad checkpoint, is an error. The
    compressed META/data bytes are copied verbatim into an exclusively new file.
    """
    input_path, output_path = Path(input_path), Path(output_path)
    with input_path.open('rb') as src:
        original_stat = os.fstat(src.fileno())
        size = original_stat.st_size
        if _read_exact(src, len(MAGIC)) != MAGIC:
            raise ValueError('unsupported DWF version')
        meta = _read_metadata(src, size)
        prefix_end = src.tell()
        index, last_time = [], 0
        state = [None] * len(meta['signals'])
        stop = 'missing index'
        while src.tell() < size:
            offset = src.tell()
            header = src.read(RECORD.size)
            if len(header) < RECORD.size:
                stop = 'incomplete record header'
                break
            tag, codec, raw_len, stored_len, _ = RECORD.unpack(header)
            if tag == b'INDX':
                stop = 'final index'
                break
            if tag != b'BLK1' or codec not in CODECS.values() or max(raw_len, stored_len) > LIMIT:
                raise ValueError('invalid data record header during recovery')
            end = offset + RECORD.size + stored_len
            if end > size:
                stop = 'incomplete final block'
                break
            src.seek(offset)
            raw = read_record(src, b'BLK1', end)
            first, last, count, before, _, after = _decode_block(meta, raw)
            if first != last_time or before != state:
                raise ValueError('checkpoint continuity mismatch during recovery')
            index.append([first, last, offset, end, count])
            last_time, state, prefix_end = last, after, end
        finalized = False
        try:
            original = Reader(src)
            finalized = original.index == index and original.index_offset == prefix_end
        except (ValueError, zlib.error):
            pass
        # Reserve only after the prefix has passed CRC and semantic validation.
        dest = output_path.open('xb')
        try:
            with dest:
                src.seek(0)
                remaining = prefix_end
                while remaining:
                    chunk = _read_exact(src, min(remaining, 8 * 1024 * 1024))
                    dest.write(chunk)
                    remaining -= len(chunk)
                offset = write_record(dest, b'INDX', json_bytes(index), 'zlib')
                dest.write(FOOTER.pack(offset, END))
                current = os.fstat(src.fileno())
                if (current.st_size, current.st_mtime_ns) != (size, original_stat.st_mtime_ns):
                    raise ValueError('input changed during recovery; use a stable snapshot')
                output_bytes = dest.tell()
        except BaseException:
            output_path.unlink(missing_ok=True)
            raise
    return dict(blocks_recovered=len(index), events_recovered=sum(r[4] for r in index),
                last_complete_time=last_time, copied_prefix_bytes=prefix_end,
                input_bytes=size, output_bytes=output_bytes,
                discarded_suffix_bytes=size - prefix_end,
                original_finalization_valid=finalized, stopped_at=stop)


def export_vcd(reader, f):
    for parts in reader.meta['header']:
        f.write(' '.join(parts) + '\n')
    for time, kind, payload in reader.events():
        if kind == 'time':
            f.write('#' + str(time) + '\n')
        elif kind == 'control':
            f.write(' '.join(payload) + '\n')
        else:
            ident, value = payload
            s = reader.meta['signals'][ident]
            if s.get('type') == 'real':
                if value[1]:
                    raise ValueError('real waveform cannot contain X/Z planes')
                raw = value[0].to_bytes(s['width'] // 8, 'little')
                number = struct.unpack('<f' if s['width'] == 32 else '<d', raw)[0]
                f.write('r' + format(number, '.17g') + ' ' + s['code'] + '\n')
                continue
            bits = bit_string(value, s['width'])
            if s['width'] == 1:
                f.write(bits + s['code'] + '\n')
            else:
                short = bits.lstrip('0') or '0'
                if bits[0] == '0' and short[0] in 'xz':
                    short = '0' + short
                if set(bits) == {'x'} or set(bits) == {'z'}:
                    short = bits[0]
                f.write('b' + short + ' ' + s['code'] + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    pack = sub.add_parser('pack')
    pack.add_argument('input', type=Path)
    pack.add_argument('output', type=Path)
    pack.add_argument('--codec', choices=CODECS, default='zstd')
    pack.add_argument('--block-events', type=int, default=16384)
    unpack = sub.add_parser('unpack')
    unpack.add_argument('input', type=Path)
    unpack.add_argument('output', type=Path)
    repair = sub.add_parser('recover', help='recover complete blocks from an interrupted DWF file')
    repair.add_argument('input', type=Path)
    repair.add_argument('output', type=Path)
    seek = sub.add_parser('window')
    seek.add_argument('input', type=Path)
    seek.add_argument('start', type=int)
    seek.add_argument('end', type=int)
    args = ap.parse_args()
    if args.command in ('pack', 'unpack', 'recover') and (args.input.resolve() == args.output.resolve()
            or (args.output.exists() and args.input.samefile(args.output))):
        ap.error('input and output must be distinct')
    if args.command == 'pack':
        with args.input.open() as src, args.output.open('wb') as dest:
            meta, stream = read_vcd_header(src)
            w = Writer(dest, meta, args.codec, args.block_events)
            for event in vcd_events(stream, meta):
                w.append(event)
            w.close()
    elif args.command == 'unpack':
        with args.input.open('rb') as src, args.output.open('w') as dest:
            export_vcd(Reader(src), dest)
    elif args.command == 'recover':
        print(json.dumps(recover(args.input, args.output)))
    else:
        with args.input.open('rb') as src:
            r = Reader(src)
            state, events = r.window(args.start, args.end)
            print(json.dumps({'state_before_start': state, 'events': events,
                              'decoded_blocks': r.decoded_blocks, 'total_blocks': len(r.index)}))


if __name__ == '__main__':
    main()
