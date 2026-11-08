// Liberty roles define the supported low-transparent enable latch. Physical
// pin names, cell names, design names and library names never select this model.
struct PowerClockGate {
    uint32_t clock=UINT32_MAX, enable=UINT32_MAX, test=UINT32_MAX, output=UINT32_MAX;
    bool valid=false;
};
PowerClockGate power_clock_gate(const Network& network, InstanceId instance,
                               const edacraft::core::LibertyCellData& cell) {
    PowerClockGate model;
    if (cell.clock_gating_integrated_cell==UINT32_MAX ||
        network.str(cell.clock_gating_integrated_cell)!="latch_posedge_precontrol" ||
        sequential_cell(cell) || cell.function!=UINT32_MAX) return model;
    for (const auto& pin:cell.pins) {
        const unsigned roles=unsigned(pin.clock_gate_clock_pin)+unsigned(pin.clock_gate_enable_pin)+
            unsigned(pin.clock_gate_test_pin)+unsigned(pin.clock_gate_out_pin);
        if (!roles && pin.direction==edacraft::core::PortDirection::Internal && pin.function==UINT32_MAX &&
            pin.internal_power.empty()) continue;
        if (roles!=1 || pin.name==UINT32_MAX) return {};
        auto* role=pin.clock_gate_out_pin?&model.output:pin.clock_gate_clock_pin?&model.clock:
                   pin.clock_gate_enable_pin?&model.enable:&model.test;
        if (*role!=UINT32_MAX || (pin.clock_gate_out_pin ?
            pin.direction!=edacraft::core::PortDirection::Output || pin.function!=UINT32_MAX :
            pin.direction!=edacraft::core::PortDirection::Input)) return {};
        const auto physical=network.find_pin(instance,network.str(pin.name));
        if (!physical || !valid(network.pin(*physical).net)) return {};
        *role=physical->id;
    }
    if (model.clock==UINT32_MAX || model.enable==UINT32_MAX || model.output==UINT32_MAX) return {};
    for (const auto& arc:cell.arcs)
        if (arc.from_pin==network.pin(PinId{model.clock}).name &&
            arc.to_pin==network.pin(PinId{model.output}).name &&
            (arc.sense==edacraft::core::LibertyTimingSense::NegativeUnate ||
             arc.sense==edacraft::core::LibertyTimingSense::NonUnate)) return {};
    model.valid=true;return model;
}

// Phase-aware vectorless state weighting. Current enable/test and the held
// enable are independent averaged states; Q is always clock & held_enable.
// It is never treated as a Boolean function of the current enable while high.
double power_clock_gate_condition(const Network& network, InstanceId instance,
    const PowerClockGate& model, std::string_view expression,
    const std::vector<Activity>& activity) {
    const auto net=[&](uint32_t pin){return network.pin(PinId{pin}).net.id;};
    std::vector<uint32_t> inputs{net(model.clock)};
    for (auto pin:{model.enable,model.test}) if (pin!=UINT32_MAX &&
        std::find(inputs.begin(),inputs.end(),net(pin))==inputs.end()) inputs.push_back(net(pin));
    auto pin_probability=[&](uint32_t pin) {return activity[network.pin(PinId{pin}).net.id].probability;};
    double disabled=1-pin_probability(model.enable);
    if (model.test!=UINT32_MAX && network.pin(PinId{model.test}).net!=network.pin(PinId{model.enable}).net)
        disabled*=1-pin_probability(model.test);
    double probability=0;
    for (size_t mask=0;mask<(size_t(1)<<inputs.size());++mask) for (unsigned held=0;held<2;++held) {
        double weight=held?1-disabled:disabled;
        for (size_t bit=0;bit<inputs.size();++bit) {
            const auto p=activity[inputs[bit]].probability;weight*=((mask>>bit)&1)?p:1-p;
        }
        const auto value=evaluate_liberty_boolean(expression,[&](std::string_view name)->std::optional<int> {
            if (name==network.str(network.pin(PinId{model.output}).name)) return int((mask&1) && held);
            for (auto pin:{model.clock,model.enable,model.test}) if (pin!=UINT32_MAX &&
                name==network.str(network.pin(PinId{pin}).name)) {
                const auto bit=std::find(inputs.begin(),inputs.end(),net(pin))-inputs.begin();
                return int((mask>>bit)&1);
            }
            return {};
        });
        if (!value) return std::numeric_limits<double>::quiet_NaN();
        if (*value) probability+=weight;
    }
    return probability;
}
