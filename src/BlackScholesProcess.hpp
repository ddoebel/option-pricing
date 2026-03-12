//
// Created by David Doebel  on 06.03.2026.
//

#ifndef QUANTENGINE_BLACKSCHOLESPROCESS_HPP
#define QUANTENGINE_BLACKSCHOLESPROCESS_HPP
#include "StochasticProcess.hpp"


class BlackScholesProcess : public StochasticProcess{
public:
    explicit BlackScholesProcess(MarketData data) : StochasticProcess(std::move(data)){}

    double drift(double t, double s) override;

    double diffusion(double t, double s) override;

    double step(double t, double s, double dt, double dW) override;

};


#endif //QUANTENGINE_BLACKSCHOLESPROCESS_HPP
