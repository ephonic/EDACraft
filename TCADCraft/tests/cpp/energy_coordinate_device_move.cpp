#include "energy_coordinate_device.h"
#include <type_traits>
// Exporting a prepared snapshot and swapping a fully allocated candidate into
// accepted storage must not introduce an allocation after publication begins.
static_assert(std::is_nothrow_move_constructible<tcad::EnergyCoordinateSnapshot>::value,
              "candidate return must move without allocating");
static_assert(std::is_nothrow_move_assignable<tcad::EnergyCoordinateSnapshot>::value,
              "Cython snapshot transfer must move without allocating");
static_assert(std::is_nothrow_move_assignable<tcad::EnergyCoordinateTransportResult>::value,
              "accepted energy-coordinate publication must not allocate");
int main() {return 0;}
