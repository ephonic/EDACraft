#include "time_engine/db_api.h"
#include <iostream>
#include <iomanip>
#include <limits>
#include <string>
#include <vector>

namespace native = edacraft::core::native;

int main(int argc, char** argv) {
    const bool write = argc == 4 && std::string(argv[2]) == "--write-lib";
    if (argc < 2 || argc > 4 || (argc == 4 && !write) ||
        (argc == 3 && std::string(argv[2]) != "--cells" &&
                      std::string(argv[2]) != "--metadata" &&
                      std::string(argv[2]) != "--model" &&
                      std::string(argv[2]) != "--extract")) {
        std::cerr << "Usage: db_native_inspect <library.db> [--cells|--metadata|--extract|--model]\n"
                  << "       db_native_inspect <library.db> --write-lib <output.lib>\n"
                  << "Standalone experiment; production DB input remains disabled.\n";
        return 2;
    }
    if (write || (argc == 3 && std::string(argv[2]) == "--model")) {
        edacraft::core::LibertyDB db; edacraft::core::StringPool pool; std::string error;
        if (!native::read_synopsys_db_native(argv[1], db, pool, &error)) {
            std::cerr << error << '\n'; return 1;
        }
        if (write && !edacraft::core::dbio::write_liberty_file(db,pool,argv[3],&error)) {
            std::cerr << error << '\n'; return 1;
        }
        const auto& lib = db.library(0); size_t pins = 0, arcs = 0, vectors = 0;
        for (uint32_t ci = 0; ci < lib.cells.size(); ++ci) {
            pins += lib.cells[ci].pins.size(); arcs += lib.cells[ci].arcs.size();
            for (const auto& a : lib.cells[ci].arcs) vectors += a.csm_output_current_rise.waveforms.size() + a.csm_output_current_fall.waveforms.size();
        }
        std::cout << "library=" << pool.view(lib.name) << "\nmodel_loaded=1\ncells=" << lib.cells.size()
                  << "\npins=" << pins << "\narcs=" << arcs << "\nCCS_vectors=" << vectors << '\n';
        return 0;
    }
    native::DbInfo info;
    std::string error;
    if (!native::probe_synopsys_db(argv[1], info, &error)) {
        std::cerr << error << '\n';
        return 1;
    }
    std::cout << "library=" << info.library_name << '\n'
              << "file_bytes=" << info.file_size << '\n'
              << "streams=" << info.stream_count << '\n'
              << "complete_streams=" << info.complete_stream_count << '\n'
              << "partial_streams=" << info.partial_stream_count << '\n'
              << "directory_cells=" << info.directory_cells << '\n'
              << "timing_model_complete=0\n";
    if (argc == 3 && std::string(argv[2]) == "--cells") {
        for (const auto& name : info.cell_names) std::cout << "cell=" << name << '\n';
    }
    if (argc == 3 && std::string(argv[2]) == "--metadata") {
        std::vector<native::CellObject> cells;
        if (!native::extract_cell_objects(argv[1], cells, &error)) {
            std::cerr << error << '\n';
            return 1;
        }
        std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
        for (const auto& cell : cells)
            std::cout << "metadata=" << cell.name << '\t' << cell.area << '\t' << cell.footprint << '\n';
    }
    if (argc == 3 && std::string(argv[2]) == "--extract") {
        std::vector<native::NldmTable> tables;
        std::vector<native::CcsVectorDoc> currents;
        std::vector<native::PortsDoc> ports;
        std::vector<native::ArcDoc> arcs;
        std::vector<native::CellObject> cells;
        if (!native::extract_cell_objects(argv[1], cells, &error) ||
            !native::extract_nldm_tables(argv[1], tables, &error) ||
            !native::extract_ccs_vectors(argv[1], currents, &error) ||
            !native::extract_ports(argv[1], ports, &error) ||
            !native::extract_arcs(argv[1], arcs, &error)) {
            std::cerr << error << '\n';
            return 1;
        }
        size_t vectors = 0, pins = 0, records = 0;
        for (const auto& doc : currents) vectors += doc.vectors.size();
        for (const auto& doc : ports) pins += doc.pins.size();
        for (const auto& doc : arcs) records += doc.arcs.size();
        std::cout << "diagnostic_cell_metadata=" << cells.size() << '\n'
                  << "diagnostic_nldm_tables=" << tables.size() << '\n'
                  << "diagnostic_ccs_vectors=" << vectors << '\n'
                  << "diagnostic_pin_records=" << pins << '\n'
                  << "diagnostic_arc_records=" << records << '\n'
                  << "note=extracted records are not a connected timing model\n";
    }
    return 0;
}
