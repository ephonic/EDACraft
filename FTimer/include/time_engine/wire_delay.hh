#pragma once

namespace te {

struct PiResponse {
    float delay = 0.0f;
    float slew = 0.0f;
};

PiResponse compute_pi_response(float c1, float rpi, float c2, float cap_scale,
                               float input_slew, float rd);

} // namespace te
