#pragma once
#include <functional>
#include <optional>
#include <string_view>

namespace te {
// Reuse the timing graph's Liberty Boolean grammar for power expressions.
std::optional<bool> evaluate_liberty_boolean(std::string_view expression,
    const std::function<std::optional<int>(std::string_view)>& lookup);
}
