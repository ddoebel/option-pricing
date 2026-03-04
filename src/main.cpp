//
// Created by David Doebel  on 03.03.2026.
//

#include "models/black_scholes.hpp"
#include "simulation/monte_carlo.hpp"
#include "models/payoff.hpp"
#include <iostream>

int main() {

    BlackScholes model(100.0, 0.05, 0.2, 1.0);
    CallPayoff payoff(100.0);

    MonteCarloEngine mc;

    double price = mc.price(model, payoff, 1000000);

    std::cout << "MC Price: " << price << std::endl;

    return 0;
}