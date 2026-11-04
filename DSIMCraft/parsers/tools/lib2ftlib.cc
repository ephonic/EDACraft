#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include "edacraft/core/liberty_db.hpp"
#include "liberty/liberty_binary.hh"
#include "liberty/liberty_parser.hh"

using namespace te;
namespace ec = edacraft::core;

static void print_usage(const char* prog) {
    std::cerr << "Usage: " << prog << " <input.lib> [-o <output.ftlib>] [--gzip]\n";
    std::cerr << "\n";
    std::cerr << "  Convert an ASCII Liberty (.lib) file to a structured binary (.ftlib) format.\n";
    std::cerr << "  The binary file can be loaded much faster than re-parsing the text file.\n";
    std::cerr << "\n";
    std::cerr << "  Options:\n";
    std::cerr << "    -o <file>    Output file path (default: <input>.ftlib)\n";
    std::cerr << "    --gzip       Compress output with gzip (produces .ftlib.gz)\n";
    std::cerr << "    -h, --help   Show this help message\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    std::string input_path;
    std::string output_path;
    bool compress = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-h" || arg == "--help") {
            print_usage(argv[0]);
            return 0;
        } else if (arg == "-o") {
            if (i + 1 >= argc) {
                std::cerr << "Error: -o requires an argument\n";
                return 1;
            }
            output_path = argv[++i];
        } else if (arg == "--gzip") {
            compress = true;
        } else if (input_path.empty() && arg[0] != '-') {
            input_path = arg;
        } else {
            std::cerr << "Error: unexpected argument: " << arg << "\n";
            return 1;
        }
    }

    if (input_path.empty()) {
        std::cerr << "Error: no input file specified\n";
        return 1;
    }

    if (output_path.empty()) {
        output_path = input_path + ".ftlib";
        if (compress) {
            // Append .gz if not already present
            if (output_path.size() < 3 ||
                output_path.compare(output_path.size() - 3, 3, ".gz") != 0) {
                output_path += ".gz";
            }
        }
    }

    std::cout << "Reading: " << input_path << "\n";

    // Parse .lib file
    std::ifstream infile(input_path);
    if (!infile) {
        std::cerr << "Error: cannot open input file: " << input_path << "\n";
        return 1;
    }

    std::ostringstream ss;
    ss << infile.rdbuf();
    std::string content = ss.str();

    std::cout << "Parsing " << content.size() << " bytes...\n";

    ec::LibertyDB db;
    ec::StringPool pool;
    parser::LibertyParser parser(content);
    parser.parse(db, pool);

    std::cout << "Libraries: " << db.library_count() << "\n";
    for (uint32_t li = 0; li < db.library_count(); ++li) {
        const auto& lib = db.library(li);
        std::cout << "  Library \"" << pool.view(lib.name) << "\": "
                  << lib.cells.size() << " cells\n";
    }
    std::cout << "Strings: " << pool.size() << "\n";

    // Write binary
    std::cout << "Writing: " << output_path;
    if (compress) std::cout << " (gzip compressed)";
    std::cout << "\n";

    std::ofstream outfile(output_path, std::ios::binary);
    if (!outfile) {
        std::cerr << "Error: cannot open output file: " << output_path << "\n";
        return 1;
    }

    if (!save_liberty_binary(db, pool, outfile, compress)) {
        std::cerr << "Error: failed to write binary\n";
        return 1;
    }

    // Report sizes
    auto in_size = std::filesystem::file_size(input_path);
    auto out_size = std::filesystem::file_size(output_path);
    std::cout << "Done.\n";
    std::cout << "  Input:  " << in_size << " bytes ("
              << (in_size / (1024.0 * 1024.0 * 1024.0)) << " GB)\n";
    std::cout << "  Output: " << out_size << " bytes ("
              << (out_size / (1024.0 * 1024.0)) << " MB)\n";
    std::cout << "  Ratio:  " << (100.0 * out_size / in_size) << "%\n";

    return 0;
}
