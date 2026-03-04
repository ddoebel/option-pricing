//
// Created by David Doebel  on 03.03.2026.
//

#ifndef OPTION_PRICING_MONTE_CARLO_HPP
#define OPTION_PRICING_MONTE_CARLO_HPP
#pragma once
#include <random>
#include <vector>

class MonteCarloEngine {
public:
    MonteCarloEngine(unsigned long seed = 42)
        : gen_(seed), dist_(0.0, 1.0) {}

    template<typename Model, typename Payoff>
    double price(const Model& model,
                 const Payoff& payoff,
                 std::size_t N) {

        double sum = 0.0;

        for (std::size_t i = 0; i < N; ++i) {
            double Z = dist_(gen_);
            double ST = model.terminal_price(Z);
            sum += payoff(ST);
        }

        return model.discount() * sum / N;
    }

private:
    std::mt19937_64 gen_;
    std::normal_distribution<> dist_;
};
#endif //OPTION_PRICING_MONTE_CARLO_HPP