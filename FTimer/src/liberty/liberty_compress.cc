#include "liberty_compress.hh"

#include <zlib.h>
#include <stdexcept>
#include <cstring>

namespace te {

std::vector<uint8_t> compress_gzip(const uint8_t* data, size_t len, int level) {
    if (len == 0) return {};
    if (level < 0 || level > 9) level = Z_DEFAULT_COMPRESSION;

    z_stream strm{};
    strm.next_in = const_cast<Bytef*>(data);
    strm.avail_in = static_cast<uInt>(len);

    int ret = deflateInit2(&strm, level, Z_DEFLATED,
                           15 + 16, // windowBits = 15 + 16 for gzip wrapper
                           8,       // memLevel
                           Z_DEFAULT_STRATEGY);
    if (ret != Z_OK) {
        throw std::runtime_error("deflateInit2 failed");
    }

    // Pre-allocate buffer; resize avoids reallocation during the loop.
    std::vector<uint8_t> out;
    out.resize(len + len / 1000 + 32);
    size_t out_pos = 0;

    do {
        if (out_pos >= out.size()) {
            out.resize(out.size() * 2);
        }
        strm.next_out = out.data() + out_pos;
        strm.avail_out = static_cast<uInt>(out.size() - out_pos);

        ret = deflate(&strm, Z_FINISH);

        out_pos = out.size() - strm.avail_out;
    } while (ret == Z_OK);

    deflateEnd(&strm);

    if (ret != Z_STREAM_END) {
        throw std::runtime_error("gzip compression failed");
    }

    out.resize(out_pos);
    return out;
}

std::vector<uint8_t> decompress_gzip(const uint8_t* data, size_t len) {
    if (len == 0) return {};

    z_stream strm{};
    strm.next_in = const_cast<Bytef*>(data);
    strm.avail_in = static_cast<uInt>(len);

    int ret = inflateInit2(&strm, 15 + 16); // windowBits + 16 for gzip
    if (ret != Z_OK) {
        throw std::runtime_error("inflateInit2 failed");
    }

    std::vector<uint8_t> out;
    out.reserve(len * 4); // heuristic: decompressed is usually larger

    const size_t CHUNK = 65536;

    do {
        size_t old_size = out.size();
        out.resize(old_size + CHUNK);
        strm.next_out = out.data() + old_size;
        strm.avail_out = CHUNK;

        ret = inflate(&strm, Z_NO_FLUSH);

        if (ret == Z_STREAM_ERROR || ret == Z_NEED_DICT ||
            ret == Z_DATA_ERROR || ret == Z_MEM_ERROR) {
            inflateEnd(&strm);
            throw std::runtime_error("gzip decompression failed");
        }

        out.resize(old_size + (CHUNK - strm.avail_out));
    } while (ret != Z_STREAM_END);

    inflateEnd(&strm);
    return out;
}

bool is_gzip_data(const uint8_t* data, size_t len) {
    return len >= 2 && data[0] == 0x1f && data[1] == 0x8b;
}

} // namespace te
