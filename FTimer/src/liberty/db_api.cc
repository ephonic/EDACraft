// Native subset imported from /home/yangfan/c906/t12/db_api.cc (2026-10-25).
// Original SHA256: 37edd6f24ad94c29405f06234875c68a6da6e1f33e0682c47e7be8afe62504ca
#include "time_engine/db_api.h"
#include "db_native_model.hh"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <unordered_map>
#include <zlib.h>

namespace edacraft::core {
namespace native {
namespace {

// Read the whole file (the CCS library is 223 MB; acceptable and the
// simplest way to allow backtracking gzip scans).
bool read_whole_file(const std::string& path, std::string& out,
                     std::string* error) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        if (error) *error = "cannot open " + path;
        return false;
    }
    in.seekg(0, std::ios::end);
    const auto size = in.tellg();
    if (size < 0) {
        if (error) *error = "cannot determine .db size: " + path;
        return false;
    }
    in.seekg(0);
    std::string data(static_cast<size_t>(size), '\0');
    if (!in.read(data.data(), static_cast<std::streamsize>(data.size()))) {
        if (error) *error = "short read of .db file: " + path;
        return false;
    }
    out.swap(data);
    return true;
}

// Decode one gzip stream starting at data[off]; returns decoded bytes
// and stores the number of consumed input bytes.  Empty result = not a
// valid gzip stream here.  When accept_partial is set, a mid-stream
// decode error still returns the output produced so far (giant streams
// are cut into <=2 MB fragments by the writer; the first fragment
// holds complete records and is recovered leniently).
bool gunzip_at(const std::string& data, size_t off, std::string& out,
               size_t* consumed, bool accept_partial = false) {
    z_stream zs{};
    if (inflateInit2(&zs, 16 + MAX_WBITS) != Z_OK) return false;
    const size_t kWindow = 8u << 20;
    std::string result;
    unsigned char buf[1 << 16];
    size_t pos = off;
    bool ok = false;
    bool errored = false;
    size_t err_pos = off;
    while (pos < data.size()) {
        size_t n = std::min(kWindow, data.size() - pos);
        zs.next_in = reinterpret_cast<Bytef*>(
            const_cast<char*>(data.data() + pos));
        zs.avail_in = static_cast<uInt>(n);
        size_t before_in = n;
        for (;;) {
            zs.next_out = buf;
            zs.avail_out = sizeof(buf);
            int rc = inflate(&zs, Z_NO_FLUSH);
            if (result.size() > (256u << 20)) { inflateEnd(&zs); return false; }
            if (rc == Z_STREAM_END) {
                result.append(reinterpret_cast<char*>(buf),
                              sizeof(buf) - zs.avail_out);
                pos += before_in - zs.avail_in;
                ok = true;
                goto finish;
            }
            if (rc == Z_OK || rc == Z_BUF_ERROR) {
                result.append(reinterpret_cast<char*>(buf),
                              sizeof(buf) - zs.avail_out);
                if (zs.avail_out != 0) break;  // need more input
                continue;
            }
            errored = true;  // Z_DATA_ERROR: fragment boundary
            // zlib may have emitted output into the buffer during the
            // erroring call — keep it (partial streams rely on it).
            result.append(reinterpret_cast<char*>(buf),
                          sizeof(buf) - zs.avail_out);
            err_pos = pos + (before_in - zs.avail_in);
            goto finish;
        }
        if (before_in == zs.avail_in) break;
        pos += before_in - zs.avail_in;
    }
finish:
    inflateEnd(&zs);
    if (ok && !result.empty()) {
        out.swap(result);
        if (consumed) *consumed = pos - off;
        return true;
    }
    // Lenient: accept substantial output even when the member never
    // reached eof — the writer stores payloads as independently
    // gzip'd fragments (<=2 MB for giants, 8 KB for smaller ones)
    // whose decompressed outputs concatenate logically.  A fragment
    // ends either on a decode error (cut mid-deflate, foreign bytes
    // follow) or when input runs out cleanly (window exhausted).
    if (accept_partial && result.size() >= 4096) {
        out.swap(result);
        if (consumed)
            *consumed = err_pos > off ? err_pos - off
                                      : (pos > off ? pos - off : 1);
        return true;
    }
    (void)errored;  // diagnosis retained: error vs clean exhaustion
    return false;
}

struct GzStream {
    size_t offset;
    size_t compressed;
    size_t plain;
    bool complete = false;
    bool root = false;
};

// Walk every valid gzip stream in the file.  Streams larger than the
// writer's 2 MB fragment cap are stored cut; their first fragment is
// recovered leniently (complete records before the cut).
void scan_gzip_streams(const std::string& d, std::vector<GzStream>& out) {
    static const std::string kMagic =
        std::string("\x1f\x8b\x08", 3);
    size_t pos = 0;
    std::string tmp;
    while (pos + 3 < d.size()) {
        size_t hit = d.find(kMagic, pos);
        if (hit == std::string::npos || hit + 3 > d.size()) break;
        size_t used = 0;
        if (gunzip_at(d, hit, tmp, &used) && used > 0) {
            out.push_back({hit, used, tmp.size(), true,
                           tmp.find(std::string(1, 15) + "db library name") < 128});
            pos = hit + used;
            continue;
        }
        size_t used2 = 0;
        std::string partial;
        if (gunzip_at(d, hit, partial, &used2, /*accept_partial=*/true) &&
            used2 > 0) {
            out.push_back({hit, used2, partial.size(), false});
            // Do not trust err_pos for scanning: inflate may consume
            // garbage past the fragment boundary and overshoot into
            // the next real stream.  Resume right after this magic.
            pos = hit + 1;
            continue;
        }
        pos = hit + 1;
    }
}

// ROOT is recognized by its own record, not by its position in the file.
// Only CRC-validated streams may supply authoritative directory metadata.
bool read_root(const std::string& data, const std::vector<GzStream>& streams,
               std::string& root, std::string* error) {
    const GzStream* found = nullptr;
    for (const auto& stream : streams) {
        if (!stream.root || !stream.complete) continue;
        if (found) {
            if (error) *error = "multiple ROOT objects: unsupported .db container";
            return false;
        }
        found = &stream;
    }
    size_t used = 0;
    if (!found || !gunzip_at(data, found->offset, root, &used)) {
        if (error) *error = "no supported CRC-valid .db ROOT object (unsupported format or corrupt file)";
        return false;
    }
    return true;
}

const char* const kTableKinds[] = {
    "cell_rise", "cell_fall", "rise_transition", "fall_transition",
    "rise_power", "fall_power",
    "rise_constraint", "fall_constraint",
    "receiver_capacitance1_rise", "receiver_capacitance1_fall",
    "receiver_capacitance2_rise", "receiver_capacitance2_fall",
};

// Find length-prefixed ASCII tokens: <len><bytes>.
size_t find_token(const std::string& d, const char* name, size_t from,
                  size_t to) {
    const size_t n = std::strlen(name);
    if (n == 0 || n > 255) return std::string::npos;
    for (size_t i = from; i + 1 + n <= to; ++i) {
        if (static_cast<unsigned char>(d[i]) == n &&
            std::memcmp(d.data() + i + 1, name, n) == 0)
            return i;
    }
    return std::string::npos;
}

// Array payload headers observed in per-object streams.  The element
// type code is 0x03 (big-endian float32) and the count is a 1..2 byte
// LEB128 varint; the leading type id varies per bag family:
//   axis arrays:   "22 03 <n>" (NLDM bags), "16 03 <n>" (constraint/
//                  template bags), ...
//   vector arrays: "3e 03 <n>" (CCS waveform bags)
//   value arrays:  "82 02 03 <n>" (all families)
constexpr int kMarkerValues = 1;  // "82 02 03"
constexpr int kMarkerAnyAxis = 2;  // "<any T> 03 <n>" (axis candidate)

// Read a LEB128 varint at d[at]; returns bytes consumed or 0.
size_t read_varint(const std::string& d, size_t at, size_t limit,
                   unsigned& value) {
    unsigned v = 0;
    int shift = 0;
    size_t i = at;
    for (int k = 0; k < 2 && i < limit; ++k, ++i) {
        unsigned char b = d[i];
        v |= static_cast<unsigned>(b & 0x7f) << shift;
        if (!(b & 0x80)) {
            value = v;
            return i + 1 - at;
        }
        shift += 7;
    }
    return 0;
}

// Decode <count> BE float32 starting at d[data] and validate the values.
bool decode_be_floats(const std::string& d, size_t at, int count,
                      std::vector<float>& out) {
    if (count < 0 || at > d.size() || static_cast<size_t>(count) > (d.size() - at) / 4) return false;
    out.resize(count);
    for (int i = 0; i < count; ++i) {
        uint32_t bits = (static_cast<uint8_t>(d[at + 4 * i]) << 24) |
                        (static_cast<uint8_t>(d[at + 4 * i + 1]) << 16) |
                        (static_cast<uint8_t>(d[at + 4 * i + 2]) << 8) |
                        static_cast<uint8_t>(d[at + 4 * i + 3]);
        float f;
        std::memcpy(&f, &bits, 4);
        if (!std::isfinite(f) || std::fabs(f) > 1e6f) return false;
        out[i] = f;
    }
    return true;
}

// Find the next array of the given marker type in [from, to); returns
// the data offset (past the header) and fills out.  monotonic
// additionally requires a positive non-decreasing sequence (true for
// Liberty table axes).  For kMarkerAnyAxis the leading type byte is
// arbitrary ("16"/"22"/... family-specific) and is reported via type_out.
size_t find_float_array(const std::string& d, size_t from, size_t to,
                        int marker, bool monotonic,
                        std::vector<float>& out,
                        uint8_t* type_out = nullptr) {
    for (size_t i = from; i < to; ++i) {
        int count = -1;
        size_t data = 0;
        uint8_t type = 0;
        if (marker == kMarkerValues) {
            if (i + 3 > to || static_cast<uint8_t>(d[i]) != 0x82 ||
                static_cast<uint8_t>(d[i + 1]) != 0x02 ||
                static_cast<uint8_t>(d[i + 2]) != 0x03)
                continue;
            unsigned n = 0;
            size_t used = read_varint(d, i + 3, to, n);
            if (used == 0 || n < 1 || n > 65535) continue;
            count = static_cast<int>(n);
            data = i + 3 + used;
            type = 0x82;
        } else {  // kMarkerAnyAxis: "<T> 03 <n>"
            if (i + 2 > to || static_cast<uint8_t>(d[i + 1]) != 0x03)
                continue;
            type = static_cast<uint8_t>(d[i]);
            if (type == 0x03 || type == 0x00) continue;  // degenerate
            unsigned n = 0;
            size_t used = read_varint(d, i + 2, to, n);
            if (used == 0 || n < 1 || n > 4096) continue;
            count = static_cast<int>(n);
            data = i + 2 + used;
        }
        if (data + static_cast<size_t>(count) * 4 > to) continue;
        std::vector<float> v;
        if (!decode_be_floats(d, data, count, v)) continue;
        if (monotonic) {
            bool mono = v[0] > 0.0f;
            for (size_t k = 1; k < v.size(); ++k)
                if (v[k] < v[k - 1] || !(v[k] > 0.0f)) { mono = false; break; }
            if (!mono) continue;
        }
        out.swap(v);
        if (type_out) *type_out = type;
        return data + static_cast<size_t>(count) * 4;
    }
    return std::string::npos;
}

void parse_nldm_from_stream(const std::string& s, std::vector<NldmTable>& out) {
    size_t pos = 0;
    while (pos < s.size()) {
        size_t kind_tok = std::string::npos;
        const char* kind_name = nullptr;
        for (const char* k : kTableKinds) {
            size_t t = find_token(s, k, pos, s.size());
            if (t != std::string::npos &&
                (kind_tok == std::string::npos || t < kind_tok)) {
                kind_tok = t;
                kind_name = k;
            }
        }
        if (kind_tok == std::string::npos) break;
        const size_t name_len = std::strlen(kind_name);
        size_t scan_from = kind_tok + 1 + name_len;
        size_t scan_to = s.size();
        for (const char* k : kTableKinds) {
            size_t t = find_token(s, k, scan_from, s.size());
            if (t != std::string::npos) scan_to = std::min(scan_to, t);
        }
        NldmTable tab;
        tab.kind = kind_name;
        // Verbose records name their arrays; compact records embed the
        // arrays directly.  Axis arrays use family-specific type codes
        // ("22" in NLDM bags, "16" in constraint/template bags, ...),
        // so extract by pattern: two monotonic axis arrays of the same
        // family followed by a values array of size n1*n2.
        std::vector<float> a1, a2, vals;
        uint8_t t1 = 0;
        size_t p1 = find_float_array(s, scan_from, scan_to, kMarkerAnyAxis,
                                     true, a1, &t1);
        bool ok = false;
        if (p1 != std::string::npos && !a1.empty()) {
            uint8_t t2 = 0;
            size_t q = p1;
            while ((q = find_float_array(s, q, scan_to, kMarkerAnyAxis, true,
                                         a2, &t2)) != std::string::npos) {
                if (t2 == t1) break;
                q += 1;  // keep scanning for a same-family axis
            }
            if (q != std::string::npos && !a2.empty() && t2 == t1) {
                const size_t want = a1.size() * a2.size();
                size_t pv = find_float_array(s, q, scan_to, kMarkerValues,
                                             false, vals);
                ok = pv != std::string::npos && vals.size() == want;
            }
            if (!ok) {
                // 1-D table (e.g. passive power tables): single axis,
                // values count == axis count, no second axis.
                size_t pv = find_float_array(s, p1, scan_to, kMarkerValues,
                                             false, vals);
                ok = pv != std::string::npos && vals.size() == a1.size();
                if (ok) a2.assign(1, 0.0f);
            }
        }
        if (ok) {
            // "template" token: <8>"template" <tag> <len> <name> — the
            // tag/len pair sits within the next 3 bytes.
            size_t it = find_token(s, "template", scan_from, scan_to);
            if (it != std::string::npos) {
                for (size_t lead = 9; lead <= 11; ++lead) {
                    if (it + lead >= scan_to) break;
                    unsigned char n = s[it + lead];
                    if (n < 4 || n > 48 || it + lead + 1 + n > scan_to)
                        continue;
                    bool printable = true;
                    for (size_t k = 1; k <= n; ++k) {
                        char c = s[it + lead + k];
                        if (static_cast<unsigned char>(c) < 0x20 ||
                            static_cast<unsigned char>(c) > 0x7e) {
                            printable = false;
                            break;
                        }
                    }
                    if (printable) {
                        tab.tmpl.assign(s, it + lead + 1, n);
                        break;
                    }
                }
            }
            tab.axis1 = std::move(a1);
            tab.axis2 = std::move(a2);
            tab.values = std::move(vals);
            out.push_back(std::move(tab));
        }
        pos = std::max(scan_to, scan_from + 1);
    }
}

// Compact records carry no inline kind name: the table is a pair of
// monotonic axis arrays followed by a values array of matching size.
// Emitted with kind "unknown".
void parse_unnamed_tables(const std::string& s, std::vector<NldmTable>& out) {
    size_t pos = 0;
    while (pos + 3 < s.size()) {
        std::vector<float> a1, a2, vals;
        uint8_t t1 = 0;
        size_t p1 = find_float_array(s, pos, s.size(), kMarkerAnyAxis, true,
                                     a1, &t1);
        if (p1 == std::string::npos) break;
        uint8_t t2 = 0;
        size_t p2 = std::string::npos;
        size_t q = p1;
        while ((q = find_float_array(s, q, s.size(), kMarkerAnyAxis, true, a2,
                                     &t2)) != std::string::npos) {
            if (t2 == t1) { p2 = q; break; }
            q += 1;
        }
        if (p2 == std::string::npos) break;
        const size_t want = a1.size() * a2.size();
        size_t pv = std::string::npos;
        if (want > 0 && want <= 65535)
            pv = find_float_array(s, p2, s.size(), kMarkerValues, false, vals);
        if (pv != std::string::npos && vals.size() == want) {
            NldmTable tab;
            tab.kind = "unknown";
            tab.axis1 = std::move(a1);
            tab.axis2 = std::move(a2);
            tab.values = std::move(vals);
            out.push_back(std::move(tab));
            pos = pv;
        } else {
            pos = p1;
        }
    }
}

// ── CCS output_current vectors ────────────────────────────────────────
// Vector object layout (verbose first record spells attribute names,
// later ones are compact; both share the markers):
//   <idx> 30 09 01
//     [03 0a 0e "reference_time"]  <ref: BE f32>          (scalar)
//     06 03 01 <slew: BE f32>
//     06 03 01 <cap: BE f32>
//     3e 03 <nt> <nt x BE f32 times>
//     [names/sizes]  3e 03 <nt> <nt x BE f32 currents>
//     09 <nt> 0a 14 00 <next idx> 30 09 01 ...
// Vectors are delimited by the trailer "09 <nt> 0a 14 00"; only the
// "0a 14 00" suffix is constant (nt = sample count varies), so the
// split uses those three bytes.
constexpr const char* kVecTail = "\x0a\x14\x00";
constexpr const char* kVecHead = "\x30\x09\x01";  // vector record start

bool read_be_f32(const std::string& d, size_t at, float& out) {
    if (at + 4 > d.size()) return false;
    uint32_t bits = (static_cast<uint8_t>(d[at]) << 24) |
                    (static_cast<uint8_t>(d[at + 1]) << 16) |
                    (static_cast<uint8_t>(d[at + 2]) << 8) |
                    static_cast<uint8_t>(d[at + 3]);
    std::memcpy(&out, &bits, 4);
    return std::isfinite(out);
}

// Collect "06 03 01 <f32>" scalars inside [from,to).
std::vector<float> scalars_in(const std::string& d, size_t from, size_t to) {
    std::vector<float> out;
    for (size_t i = from; i + 7 <= to; ++i) {
        if (static_cast<uint8_t>(d[i]) == 0x06 &&
            static_cast<uint8_t>(d[i + 1]) == 0x03 &&
            static_cast<uint8_t>(d[i + 2]) == 0x01) {
            float f;
            if (read_be_f32(d, i + 3, f)) out.push_back(f);
        }
    }
    return out;
}

// Collect "<T> 03 <n> <n f32>" arrays inside [from,to).  The type
// byte varies per record (observed 3e/3a/56/22/16/...); the element
// code is 0x03 (BE float32) and the count is a varint.  n >= 4 keeps
// the "06 03 01" scalar markers (n = 1) out of the result.
std::vector<std::vector<float>> vec_arrays_in(const std::string& d, size_t from,
                                              size_t to) {
    std::vector<std::vector<float>> out;
    for (size_t i = from; i + 3 <= to;) {
        if (static_cast<uint8_t>(d[i + 1]) == 0x03) {
            uint8_t type = static_cast<uint8_t>(d[i]);
            if (type != 0x03 && type != 0x00 && type != 0x06) {
                unsigned n = 0;
                size_t used = read_varint(d, i + 2, to, n);
                if (used > 0 && n >= 4 && n <= 255 &&
                    i + 2 + used + static_cast<size_t>(n) * 4 <= to) {
                    std::vector<float> v;
                    if (decode_be_floats(d, i + 2 + used, static_cast<int>(n), v)) {
                        out.push_back(std::move(v));
                        i += 2 + used + static_cast<size_t>(n) * 4;
                        continue;
                    }
                }
            }
        }
        ++i;
    }
    return out;
}

void parse_ccs_vectors(const std::string& s, size_t stream_off,
                       const std::string& group,
                       std::vector<CcsVectorDoc>& out) {
    // Vector records end with the trailer "09 0f 0a 14 00"; the next
    // record starts with "<idx> 30 09 01".  Split on the trailer and
    // parse each region; the verbose first record spells attribute
    // names, compact ones only carry the markers.
    std::vector<size_t> tails;
    for (size_t i = 0; i + 3 <= s.size(); ++i)
        if (std::memcmp(s.data() + i, kVecTail, 3) == 0) tails.push_back(i);
    if (tails.empty()) return;
    CcsVectorDoc doc;
    doc.group = group;
    doc.stream_offset = stream_off;
    bool any = false;
    size_t region_start = 0;
    for (size_t m = 0; m < tails.size(); ++m) {
        size_t from = region_start;
        size_t to = tails[m] + 3;  // include trailer
        region_start = to;
        // the vector header "30 09 01" must be present in the region
        size_t h = std::string::npos;
        for (size_t i = from; i + 3 <= to; ++i)
            if (std::memcmp(s.data() + i, kVecHead, 3) == 0) { h = i; break; }
        if (h == std::string::npos) continue;

        float slew = 0.0f, cap = 0.0f, ref = -1.0f;
        std::vector<float> times, currents;
        bool ok = false;
        // strict compact walk:
        //   <ref> 02 06 03 01 <slew> 03 01 04 06 03 01 <cap> ...
        if (h + 3 + 4 + 1 + 3 + 4 + 3 + 3 + 4 <= to) {
            size_t p = h + 3;
            if (read_be_f32(s, p, ref) && ref >= 0.0f && ref < 1.0f &&
                static_cast<uint8_t>(s[p + 4]) == 0x02 &&
                static_cast<uint8_t>(s[p + 5]) == 0x06 &&
                static_cast<uint8_t>(s[p + 6]) == 0x03 &&
                static_cast<uint8_t>(s[p + 7]) == 0x01) {
                size_t q = p + 8;
                if (read_be_f32(s, q, slew) && slew > 0.0f &&
                    static_cast<uint8_t>(s[q + 4]) == 0x03 &&
                    static_cast<uint8_t>(s[q + 5]) == 0x01 &&
                    static_cast<uint8_t>(s[q + 6]) == 0x04 &&
                    static_cast<uint8_t>(s[q + 7]) == 0x06 &&
                    static_cast<uint8_t>(s[q + 8]) == 0x03 &&
                    static_cast<uint8_t>(s[q + 9]) == 0x01) {
                    size_t r = q + 10;
                    if (read_be_f32(s, r, cap) && cap > 0.0f) {
                        size_t a = r + 4;
                        auto arrs = vec_arrays_in(s, a, to);
                        if (arrs.size() >= 2 && arrs[0].size() == arrs[1].size() &&
                            !arrs[0].empty()) {
                            times = arrs[0];
                            currents = arrs[1];
                            ok = true;
                        }
                    }
                }
            }
        }
        if (!ok) {
            // verbose form: attribute names spelled between the values
            auto sc = scalars_in(s, h + 3, to);
            auto arrs = vec_arrays_in(s, h + 3, to);
            size_t rt = find_token(s, "reference_time", from, to);
            if (rt != std::string::npos) {
                for (size_t lead = 15; lead <= 19 && ref < 0.0f; ++lead)
                    if (rt + lead + 4 <= to) {
                        float f;
                        if (read_be_f32(s, rt + lead, f) && f >= 0.0f &&
                            f < 1.0f)
                            ref = f;
                    }
            }
            if (ref >= 0.0f && sc.size() >= 2 && arrs.size() >= 2 &&
                arrs[0].size() == arrs[1].size() && !arrs[0].empty() &&
                sc[0] > 0.0f && sc[1] > 0.0f) {
                slew = sc[0];
                cap = sc[1];
                times = arrs[0];
                currents = arrs[1];
                ok = true;
            }
        }
        if (!ok || times.empty()) continue;
        bool mono = true;
        for (size_t k = 1; k < times.size(); ++k)
            if (times[k] < times[k - 1]) { mono = false; break; }
        if (!mono) continue;
        CcsVector v;
        v.ref_time = ref;
        v.slew = slew;
        v.cap = cap;
        v.times = std::move(times);
        v.currents = std::move(currents);
        doc.vectors.push_back(std::move(v));
        any = true;
    }
    if (any) out.push_back(std::move(doc));
}

// ── cell objects ──────────────────────────────────────────────────────
// Cell stream fragment (verbose):
//   <id> <len> "<CELLNAME>" ... "area" <BE f32>
//   ... "cell_footprint" <tag> <len> "<footprint>"
void parse_cell_objects(const std::string& s, size_t stream_off,
                        const std::set<std::string>& directory_names,
                        std::vector<CellObject>& out) {
    size_t pos = 0;
    while (pos < s.size()) {
        size_t a = find_token(s, "area", pos, s.size());
        if (a == std::string::npos) break;
        // value float within the next 16 bytes
        float area = 0.0f;
        bool have_area = false;
        for (size_t lead = 5; lead <= 15 && !have_area; ++lead)
            have_area = read_be_f32(s, a + lead, area) && area > 0.0f &&
                        area < 1e5f;
        // cell name: nearest structural-directory name within 768 bytes
        // before "area"; metadata attribution remains diagnostic only
        std::string name;
        size_t lower = a > 768 ? a - 768 : 0;
        for (size_t i = a > 0 ? a - 1 : 0; i > lower; --i) {
            unsigned char len = s[i];
            if (len < 1 || i + 1 + len > a) continue;
            std::string cand = s.substr(i + 1, len);
            if (directory_names.count(cand) && std::all_of(cand.begin(), cand.end(), [](char c) {
                    unsigned char u = static_cast<unsigned char>(c);
                    return u >= 0x21 && u <= 0x7e;
                })) {
                name = cand;
                break;
            }
        }
        if (have_area && directory_names.count(name)) {
            CellObject c;
            c.name = name;
            c.area = area;
            c.stream_offset = stream_off;
            // footprint value after the cell_footprint token
            size_t fp = find_token(s, "cell_footprint", a, s.size());
            if (fp != std::string::npos) {
                for (size_t lead = 15; lead <= 19; ++lead) {
                    if (fp + lead >= s.size()) break;
                    unsigned char n = s[fp + lead];
                    if (n < 3 || n > 32 || fp + lead + 1 + n > s.size())
                        continue;
                    std::string cand = s.substr(fp + lead + 1, n);
                    bool printable = std::all_of(cand.begin(), cand.end(),
                                                 [](char ch) {
                                                     unsigned char u =
                                                         static_cast<unsigned char>(ch);
                                                     return u >= 0x21 && u <= 0x7e;
                                                 });
                    if (printable) { c.footprint = cand; break; }
                }
            }
            out.push_back(std::move(c));
        }
        pos = a + 4;
    }
}

} // namespace

bool probe_synopsys_db(const std::string& path, DbInfo& info,
                       std::string* error) {
    std::string d;
    if (!read_whole_file(path, d, error)) return false;
    static const unsigned char kMagic[8] = {0x03, 0x17, 0x10, 0x63,
                                            0x00, 0x40, 0xff, 0x03};
    if (d.size() < 16 || std::memcmp(d.data(), kMagic, 8) != 0) {
        if (error) *error = "not a Synopsys .db (bad magic)";
        return false;
    }
    info = DbInfo{};
    info.file_size = d.size();
    std::vector<GzStream> streams;
    scan_gzip_streams(d, streams);
    info.stream_count = static_cast<uint32_t>(streams.size());
    for (const auto& s : streams) {
        if (s.complete) ++info.complete_stream_count;
        else ++info.partial_stream_count;
        info.compressed_bytes += s.compressed;
        info.uncompressed_bytes += s.plain;
    }
    // Decode stream #0 (the interned-string dictionary): records
    // "05 <id> <len> <chars>".
    if (!streams.empty()) {
        std::string dict;
        size_t used = 0;
        if (gunzip_at(d, streams[0].offset, dict, &used)) {
            for (size_t i = 0; i + 3 < dict.size();) {
                if (static_cast<unsigned char>(dict[i]) == 0x05) {
                    unsigned id = static_cast<unsigned char>(dict[i + 1]);
                    unsigned len = static_cast<unsigned char>(dict[i + 2]);
                    if (len > 0 && i + 3 + len <= dict.size()) {
                        std::string sv = dict.substr(i + 3, len);
                        bool printable = true;
                        for (char c : sv)
                            if (static_cast<unsigned char>(c) < 0x20 ||
                                static_cast<unsigned char>(c) > 0x7e)
                                printable = false;
                        ++info.dictionary_entries;
                        (void)printable;
                        (void)id;
                        i += 3 + len;
                        continue;
                    }
                }
                ++i;
            }
        }
    }
    std::string root;
    if (!read_root(d, streams, root, error)) return false;
    const size_t t = find_token(root, "db library name", 0, root.size());
    info.library_name.clear();
    if (t != std::string::npos) {
        // ROOT strings are <interned-id varint><length><bytes>. In the
        // supplied library the length is 35 (0x23, ASCII '#'); it is not
        // a '#' sentinel. Searching for '#' breaks other library names.
        size_t at = t + 16;
        unsigned count = 0;
        while (at < root.size() && count++ < 5) {
            const auto byte = static_cast<unsigned char>(root[at++]);
            if (!(byte & 0x80)) {
                if (at < root.size()) {
                    const size_t length = static_cast<unsigned char>(root[at++]);
                    if (length && length <= root.size() - at &&
                        std::all_of(root.begin() + at, root.begin() + at + length,
                            [](unsigned char ch) { return ch >= 0x21 && ch <= 0x7e; }))
                        info.library_name = root.substr(at, length);
                }
                break;
            }
        }
    }
    if (info.library_name.empty()) {
        if (error) *error = "missing or unsupported ROOT library-name record";
        return false;
    }
    std::vector<std::string> names;
    if (!parse_root_cell_names(root, names, error)) return false;
    info.directory_cells = names.size();
    info.cell_names = std::move(names);

    return true;
}

bool extract_nldm_tables(const std::string& path, std::vector<NldmTable>& out,
                         std::string* error) {
    std::string d;
    if (!read_whole_file(path, d, error)) return false;
    static const unsigned char kMagic[8] = {0x03, 0x17, 0x10, 0x63,
                                            0x00, 0x40, 0xff, 0x03};
    if (d.size() < 16 || std::memcmp(d.data(), kMagic, 8) != 0) {
        if (error) *error = "not a Synopsys .db (bad magic)";
        return false;
    }
    std::vector<GzStream> streams;
    scan_gzip_streams(d, streams);
    out.clear();
    std::string plain;
    for (size_t si = 0; si < streams.size(); ++si) {
        // Skip stream #0 (mixed metadata/string table).
        if (si == 0) continue;
        const auto& s = streams[si];
        size_t used = 0;
        if (!gunzip_at(d, s.offset, plain, &used, true) || plain.empty()) continue;
        const size_t before = out.size();
        parse_nldm_from_stream(plain, out);
        if (out.size() == before)
            parse_unnamed_tables(plain, out);  // compact records, no names
    }
    return true;
}

bool extract_ccs_vectors(const std::string& path,
                         std::vector<CcsVectorDoc>& out,
                         std::string* error) {
    std::string d;
    if (!read_whole_file(path, d, error)) return false;
    static const unsigned char kMagic[8] = {0x03, 0x17, 0x10, 0x63,
                                            0x00, 0x40, 0xff, 0x03};
    if (d.size() < 16 || std::memcmp(d.data(), kMagic, 8) != 0) {
        if (error) *error = "not a Synopsys .db (bad magic)";
        return false;
    }
    std::vector<GzStream> streams;
    scan_gzip_streams(d, streams);
    out.clear();
    std::string plain;
    for (size_t si = 0; si < streams.size(); ++si) {
        if (si == 0) continue;
        const auto& s = streams[si];
        size_t used = 0;
        if (!gunzip_at(d, s.offset, plain, &used, true) || plain.empty()) continue;
        // CCS vector carriers: named output_current objects or compact
        // streams with the vector record trailer + float arrays.  The
        // rise/fall group is only known when exactly one object name
        // is present (carriers may pack both, or none).
        bool is_ccs = false;
        std::string group;
        size_t gr = find_token(plain, "output_current_rise", 0, plain.size());
        size_t gf = find_token(plain, "output_current_fall", 0, plain.size());
        if (gr != std::string::npos && gf == std::string::npos) {
            is_ccs = true;
            group = "output_current_rise";
        } else if (gf != std::string::npos && gr == std::string::npos) {
            is_ccs = true;
            group = "output_current_fall";
        } else if (gr != std::string::npos) {
            is_ccs = true;  // both: mixed carrier, group unknown
        }
        if (!is_ccs) {
            size_t tails = 0;
            for (size_t i = 0; i + 3 <= plain.size(); ++i)
                if (std::memcmp(plain.data() + i, kVecTail, 3) == 0) ++tails;
            if (tails >= 4) {
                // probe arrays over the whole stream (verbose preambles
                // can exceed 8 KB before the first vector record)
                auto arr = vec_arrays_in(plain, 0, plain.size());
                if (arr.size() >= 2) is_ccs = true;
            }
        }
        if (is_ccs) parse_ccs_vectors(plain, s.offset, group, out);
    }
    return true;
}

bool extract_cell_objects(const std::string& path,
                          std::vector<CellObject>& out,
                          std::string* error) {
    std::string d;
    if (!read_whole_file(path, d, error)) return false;
    static const unsigned char kMagic[8] = {0x03, 0x17, 0x10, 0x63,
                                            0x00, 0x40, 0xff, 0x03};
    if (d.size() < 16 || std::memcmp(d.data(), kMagic, 8) != 0) {
        if (error) *error = "not a Synopsys .db (bad magic)";
        return false;
    }
    std::vector<GzStream> streams;
    scan_gzip_streams(d, streams);
    std::string root;
    if (!read_root(d, streams, root, error)) return false;
    std::vector<std::string> names;
    if (!parse_root_cell_names(root, names, error)) return false;
    const std::set<std::string> directory_names(names.begin(), names.end());
    out.clear();
    std::string plain;
    for (size_t si = 0; si < streams.size(); ++si) {
        if (si == 0) continue;
        const auto& s = streams[si];
        size_t used = 0;
        if (!gunzip_at(d, s.offset, plain, &used, true) || plain.empty()) continue;
        parse_cell_objects(plain, s.offset, directory_names, out);
    }
    // One cell may span multiple streams; keep the first record per name.
    std::stable_sort(out.begin(), out.end(),
                     [](const CellObject& a, const CellObject& b) {
                         return a.stream_offset < b.stream_offset;
                     });
    std::unordered_map<std::string, bool> seen;
    std::vector<CellObject> uniq;
    uniq.reserve(out.size());
    for (auto& c : out) {
        if (seen[c.name]) continue;
        seen[c.name] = true;
        uniq.push_back(std::move(c));
    }
    out.swap(uniq);
    return true;
}

bool parse_stream_tables(const std::string& stream_plain,
                         std::vector<NldmTable>& out) {
    const size_t before = out.size();
    parse_nldm_from_stream(stream_plain, out);
    if (out.size() == before)
        parse_unnamed_tables(stream_plain, out);
    return true;
}

bool parse_stream_ccs(const std::string& stream_plain, size_t stream_offset,
                      const std::string& group,
                      std::vector<CcsVectorDoc>& out) {
    parse_ccs_vectors(stream_plain, stream_offset, group, out);
    return true;
}

// ── ROOT cell directory ───────────────────────────────────────────────
namespace {
size_t scan_varint(const std::string& d, size_t i, unsigned& value) {
    value = 0;
    for (unsigned shift = 0; shift < 35 && i < d.size(); shift += 7) {
        const unsigned char b = static_cast<unsigned char>(d[i++]);
        if (shift == 28 && (b & 0xf0)) return std::string::npos;
        value |= static_cast<unsigned>(b & 0x7f) << shift;
        if (!(b & 0x80)) return i;
    }
    return std::string::npos;
}
} // namespace

bool parse_root_cell_names(const std::string& root, std::vector<std::string>& out,
                           std::string* error) {
    std::vector<std::pair<size_t, std::string>> names;
    for (size_t i = 0; i < root.size(); ++i) {
        const auto n = static_cast<unsigned char>(root[i]);
        if (!n || n > root.size() - i - 1) continue;
        const size_t end = i + 1 + n;
        if (!std::all_of(root.begin() + i + 1, root.begin() + end,
                        [](unsigned char ch) { return ch >= 0x21 && ch <= 0x7e; }))
            continue;
        unsigned owner = 0;
        const auto marker = scan_varint(root, end, owner);
        if (marker == std::string::npos || root.size() - marker < 4 ||
            root.compare(marker, 4, "\x81\x40\x00\x10", 4) != 0) continue;
        names.push_back({i, root.substr(i + 1, n)});
        i = marker + 2;
    }
    std::set<std::string> seen;
    std::vector<std::string> result;
    for (const auto& entry : names) {
        if (!seen.insert(entry.second).second) {
            if (error) *error = "duplicate cell in ROOT directory: " + entry.second;
            return false;
        }
        result.push_back(entry.second);
    }
    if (result.empty()) {
        if (error) *error = "no structural cell directory in ROOT";
        return false;
    }
    out.swap(result);
    return true;
}

bool extract_cell_links(const std::string& path,
                        std::vector<CellLink>& out,
                        std::string* error) {
    std::string d;
    if (!read_whole_file(path, d, error)) return false;
    static const unsigned char kMagic[8] = {0x03, 0x17, 0x10, 0x63,
                                            0x00, 0x40, 0xff, 0x03};
    if (d.size() < 16 || std::memcmp(d.data(), kMagic, 8) != 0) {
        if (error) *error = "not a Synopsys .db (bad magic)";
        return false;
    }
    std::vector<GzStream> streams;
    scan_gzip_streams(d, streams);
    // stream extents for pointer resolution
    std::vector<std::pair<size_t, size_t>> ext;  // [start, end)
    ext.reserve(streams.size());
    for (auto& s : streams) ext.push_back({s.offset, s.offset + s.compressed});
    std::sort(ext.begin(), ext.end());

    std::string root;
    if (!read_root(d, streams, root, error)) return false;

    auto resolve = [&](size_t page) -> size_t {
        size_t off = page * 0x100;
        auto it = std::upper_bound(ext.begin(), ext.end(),
                                   std::make_pair(off, SIZE_MAX));
        if (it == ext.begin()) return SIZE_MAX;
        --it;
        if (off >= it->first && off < it->second) return it->first;
        return SIZE_MAX;
    };

    out.clear();
    std::vector<std::pair<size_t, std::string>> names;
    for (size_t i = 0; i < root.size(); ++i) {
        const auto n = static_cast<unsigned char>(root[i]);
        if (!n || n > root.size() - i - 1) continue;
        const size_t end = i + 1 + n;
        if (!std::all_of(root.begin() + i + 1, root.begin() + end,
                        [](unsigned char ch) { return ch >= 0x21 && ch <= 0x7e; }))
            continue;
        unsigned owner = 0;
        const auto marker = scan_varint(root, end, owner);
        if (marker == std::string::npos || root.size() - marker < 4 ||
            root.compare(marker, 4, "\x81\x40\x00\x10", 4) != 0) continue;
        names.push_back({i, root.substr(i + 1, n)});
        i = marker + 2;
    }
    out.reserve(names.size());
    for (size_t k = 0; k < names.size(); ++k) {
        size_t end = k + 1 < names.size() ? names[k + 1].first : root.size();
        const std::string& name = names[k].second;
        size_t j = names[k].first + 1 + name.size();
        CellLink link;
        link.cell = name;
        int guard = 0;
        while (j + 4 < end && guard++ < 48) {
            unsigned char tag = root[j];
            unsigned id = 0;
            size_t j2 = scan_varint(root, j + 1, id);
            if (j2 == std::string::npos || j2 >= end) { ++j; continue; }
            size_t v = j2, ve = v;
            while (ve < end && root[ve] != 0) ++ve;
            if (ve >= end - 1 || root[ve + 1] != 0) { ++j; continue; }
            unsigned long val = 0;
            for (size_t b = ve; b-- > v;)
                val = (val << 8) | static_cast<unsigned char>(root[b]);
            if ((tag == 0x11 || tag == 0x14) && val > 0 && val <= d.size() / 0x100) {
                size_t s = resolve(static_cast<size_t>(val));
                if (s != SIZE_MAX) link.cell_object_stream = s;
            } else if (tag >= 0x15 && tag <= 0x18 && val > 0 && val <= d.size() / 0x100) {
                link.carrier_pages.push_back(static_cast<size_t>(val));
                size_t s = resolve(static_cast<size_t>(val));
                if (s != SIZE_MAX &&
                    std::find(link.carrier_streams.begin(),
                              link.carrier_streams.end(), s) ==
                        link.carrier_streams.end())
                    link.carrier_streams.push_back(s);
            }
            j = ve + 2;
        }
        out.push_back(std::move(link));
    }
    return true;
}

void attribute_ccs_by_cell(const std::vector<CellLink>& links,
                           std::vector<CcsVectorDoc>& docs) {
    for (auto& doc : docs) doc.cell.clear();
    // Carriers pack several cells; a doc may therefore be reachable from
    // multiple CellLinks.  Attribute to the first listing cell and keep
    // additional owners in owners[] for callers needing the full set.
    for (auto& doc : docs) doc.owners.clear();
    for (const auto& link : links) {
        for (size_t cs : link.carrier_streams) {
            for (auto& doc : docs) {
                if (doc.stream_offset != cs) continue;
                if (doc.cell.empty()) doc.cell = link.cell;
                bool known = false;
                for (auto& o : doc.owners)
                    if (o == link.cell) { known = true; break; }
                if (!known) doc.owners.push_back(link.cell);
            }
        }
    }
}

// ── ports streams (per-cell pin bundles) ──────────────────────────────
namespace {
// Pin electrical data in ports streams (validated against SDBD):
//  - pin names:  "<len [1..6]><NAME [A-Z0-9]>" followed within 6 bytes
//    by the slot marker "81 40" (pg rails VDD/VSS/VPP/VBB excluded).
//  - first pin's electricals are VERBOSE:  "<idx> 03 <id> <len>'capacitance' <BE f32>"
//    for the 7 cap attributes (capacitance .. fall_capacitance_upper) and
//    "<idx> <len>'max_capacitance' <f32>" for output pins.
//  - later pins are COMPACT: the 7 floats back-to-back as
//    "03 <f32> 04 <f32> ... 09 <f32>" (idx bytes 03..09, 4-byte BE values).
//  Both forms carry identical bit-exact values (verified: A2 cap 0.0015261).
void parse_ports_stream(const std::string& s, size_t stream_off,
                        std::vector<PortsDoc>& out) {
    static const char* kRail[] = {"VDD", "VSS", "VPP", "VBB"};
    static const size_t kNumRail = 4;
    auto is_rail = [&](const std::string& n) {
        for (size_t i = 0; i < kNumRail; ++i)
            if (n == kRail[i]) return true;
        return false;
    };
    // pin names
    struct NameRec { size_t pos; std::string name; };
    std::vector<NameRec> names;
    for (size_t i = 0x60; i + 7 < s.size(); ++i) {
        unsigned char len = s[i];
        if (len < 1 || len > 6 || i + 1 + len + 6 > s.size()) continue;
        std::string nm = s.substr(i + 1, len);
        if (is_rail(nm)) continue;
        bool ok = true;
        for (char c : nm) {
            unsigned u = static_cast<unsigned char>(c);
            if (!((u >= 'A' && u <= 'Z') || (u >= '0' && u <= '9'))) {
                ok = false;
                break;
            }
        }
        if (!ok) continue;
        if (s.compare(i + 1 + len, 2, "\x81\x40", 2) == 0 ||
            s.compare(i + 1 + len + 1, 2, "\x81\x40", 2) == 0 ||
            s.compare(i + 1 + len + 2, 2, "\x81\x40", 2) == 0)
            names.push_back({i, nm});
    }
    if (names.empty()) return;
    PortsDoc doc;
    doc.stream_offset = stream_off;
    auto val_after = [&](const std::string& blk, size_t tok, size_t limit,
                         float& out_v) -> bool {
        for (size_t lead = 9; lead <= 18; ++lead)
            if (tok + lead + 4 <= limit) {
                float v;
                if (read_be_f32(blk, tok + lead, v) && v > 0 && v < 0.05f) {
                    out_v = v;
                    return true;
                }
            }
        return false;
    };
    for (size_t k = 0; k < names.size(); ++k) {
        size_t end = k + 1 < names.size()
                         ? names[k + 1].pos
                         : std::min(s.size(), names[k].pos + 800);
        const std::string blk = s.substr(names[k].pos, end - names[k].pos);
        PinObject p;
        p.name = names[k].name;
        // compact: 03 <f32> 04 <f32> ... 09 <f32>  (input pins)
        float vals[7] = {-1, -1, -1, -1, -1, -1, -1};
        for (size_t j = 0; j + 5 + 6 * 5 < blk.size(); ++j) {
            if (static_cast<uint8_t>(blk[j]) != 0x03) continue;
            float v[7];
            size_t q = j;
            bool ok = true;
            for (int idx = 3; idx <= 9; ++idx) {
                if (q + 5 > blk.size() ||
                    static_cast<uint8_t>(blk[q]) != idx) {
                    ok = false;
                    break;
                }
                v[idx - 3] = -1;
                read_be_f32(blk, q + 1, v[idx - 3]);
                if (!(v[idx - 3] > 0 && v[idx - 3] < 0.05f)) {
                    ok = false;
                    break;
                }
                q += 5;
            }
            if (ok) {
                std::memcpy(vals, v, sizeof vals);
                break;
            }
        }
        p.capacitance = vals[0];
        p.rise_capacitance = vals[1];
        p.fall_capacitance = vals[2];
        // verbose attrs (fill gaps + max/min for outputs)
        size_t xt = find_token(blk, "max_capacitance", 0, blk.size());
        size_t nt = find_token(blk, "min_capacitance", 0, blk.size());
        float v;
        if (xt != std::string::npos &&
            val_after(blk, xt,
                      nt != std::string::npos ? nt : blk.size(), v))
            p.max_capacitance = v;
        if (nt != std::string::npos && val_after(blk, nt, blk.size(), v))
            p.min_capacitance = v;
        if (p.capacitance < 0) {
            size_t ct = find_token(blk, "capacitance", 0, blk.size());
            if (ct != std::string::npos && val_after(blk, ct, blk.size(), v))
                p.capacitance = v;
        }
        // direction: pin names followed by compact caps are inputs;
        // pins with max_capacitance are outputs
        if (p.capacitance > 0)
            p.direction = 0;  // input
        else if (p.max_capacitance > 0)
            p.direction = 1;  // output
        if (p.capacitance > 0 || p.max_capacitance > 0)
            doc.pins.push_back(std::move(p));
    }
    if (!doc.pins.empty()) out.push_back(std::move(doc));
}
} // namespace

// ── timing-arc streams ────────────────────────────────────────────────
namespace {
void parse_arcs_stream(const std::string& s, size_t stream_off,
                       std::vector<ArcDoc>& out) {
    size_t kt = find_token(s, "timing", 0x60, s.size());
    if (kt == std::string::npos) return;
    ArcDoc doc;
    doc.stream_offset = stream_off;
    // when conditions: length-prefixed printable strings with & or !
    for (size_t i = 0x60; i + 2 < s.size(); ++i) {
        unsigned char len = s[i];
        if (len < 3 || len > 40 || i + 1 + len > s.size()) continue;
        std::string cand = s.substr(i + 1, len);
        if (cand.find('&') == std::string::npos &&
            cand.find('!') == std::string::npos) continue;
        if (cand.find("==") != std::string::npos) continue;
        bool printable = true;
        for (char c : cand) {
            unsigned u = static_cast<unsigned char>(c);
            if (u < 0x20 || u > 0x7e) { printable = false; break; }
        }
        if (!printable) continue;
        ArcObject arc;
        arc.when = cand;
        size_t j = i + 1 + len;
        size_t se = std::min(s.size(), j + 200);
        for (size_t q = j; q + 4 < se; ++q) {
            if (s[q] == 0x2e && arc.owner_pin_index < 0) {
                for (size_t lead = 1; lead <= 4; ++lead)
                    if (q + lead < se &&
                        static_cast<unsigned char>(s[q + lead]) < 100) {
                        arc.owner_pin_index = s[q + lead];
                        break;
                    }
            }
            if (s[q] == 0x2f && arc.related_pins_index < 0) {
                for (size_t lead = 1; lead <= 4; ++lead)
                    if (q + lead < se &&
                        static_cast<unsigned char>(s[q + lead]) < 100) {
                        arc.related_pins_index = s[q + lead];
                        break;
                    }
            }
        }
        doc.arcs.push_back(std::move(arc));
        i += len;
    }
    if (!doc.arcs.empty()) out.push_back(std::move(doc));
}
} // namespace

bool extract_arcs(const std::string& path,
                  std::vector<ArcDoc>& out,
                  std::string* error) {
    std::string d;
    if (!read_whole_file(path, d, error)) return false;
    static const unsigned char kMagic[8] = {0x03, 0x17, 0x10, 0x63,
                                            0x00, 0x40, 0xff, 0x03};
    if (d.size() < 16 || std::memcmp(d.data(), kMagic, 8) != 0) {
        if (error) *error = "not a Synopsys .db (bad magic)";
        return false;
    }
    std::vector<GzStream> streams;
    scan_gzip_streams(d, streams);
    out.clear();
    std::string plain;
    for (size_t si = 0; si < streams.size(); ++si) {
        if (si == 0) continue;
        const auto& s = streams[si];
        size_t used = 0;
        if (!gunzip_at(d, s.offset, plain, &used, true) || plain.empty())
            continue;
        parse_arcs_stream(plain, s.offset, out);
    }
    return true;
}

// The imported diagnostic scanners cannot establish ownership. Model input
// uses the separate checked directory/schema decoder and explicit indices.
bool read_synopsys_db_native(const std::string& path, LibertyDB& db,
                             StringPool& pool, std::string* error) {
    return detail::read_model(path, db, pool, error);
}

bool extract_ports(const std::string& path,
                   std::vector<PortsDoc>& out,
                   std::string* error) {
    std::string d;
    if (!read_whole_file(path, d, error)) return false;
    static const unsigned char kMagic[8] = {0x03, 0x17, 0x10, 0x63,
                                            0x00, 0x40, 0xff, 0x03};
    if (d.size() < 16 || std::memcmp(d.data(), kMagic, 8) != 0) {
        if (error) *error = "not a Synopsys .db (bad magic)";
        return false;
    }
    std::vector<GzStream> streams;
    scan_gzip_streams(d, streams);
    // cell attribution map: stream offset -> cell name (tags 11/14)
    std::vector<CellLink> links;
    {
        std::string e2;
        extract_cell_links(path, links, &e2);
    }
    std::unordered_map<size_t, std::string> owner;
    for (auto& l : links) {
        // tag 11/14 pointers resolved to cell_object_stream; also try
        // carrier pages pointing at ports streams
        if (l.cell_object_stream != SIZE_MAX &&
            !owner.count(l.cell_object_stream))
            owner[l.cell_object_stream] = l.cell;
    }
    // ports streams often sit at tag-15..18 page targets: map pages too
    std::unordered_map<size_t, std::string> page_owner;
    for (auto& l : links)
        for (size_t p : l.carrier_pages) {
            size_t off = p * 0x100;
            if (!page_owner.count(off)) page_owner[off] = l.cell;
        }

    out.clear();
    std::string plain;
    for (size_t si = 0; si < streams.size(); ++si) {
        if (si == 0) continue;
        const auto& s = streams[si];
        size_t used = 0;
        if (!gunzip_at(d, s.offset, plain, &used, true) || plain.empty())
            continue;
        if (plain.find("ports") == std::string::npos) continue;
        size_t before = out.size();
        parse_ports_stream(plain, s.offset, out);
        if (out.size() == before) continue;
        PortsDoc& doc = out.back();
        auto it = owner.find(s.offset);
        if (it != owner.end()) {
            doc.cell = it->second;
            continue;
        }
        // fall back: nearest cell page pointer inside this stream's extent
        size_t best = SIZE_MAX;
        for (auto& kv : page_owner) {
            size_t p = kv.first;
            if (p >= s.offset && p < s.offset + used) {
                if (best == SIZE_MAX || p < best) best = p;
            }
        }
        if (best != SIZE_MAX) doc.cell = page_owner[best];
    }
    // drop docs without pins
    out.erase(std::remove_if(out.begin(), out.end(),
                             [](const PortsDoc& p) { return p.pins.empty(); }),
              out.end());
    return true;
}

} // namespace native
} // namespace edacraft::core
