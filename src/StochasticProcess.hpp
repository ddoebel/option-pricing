//
// Created by David Doebel  on 05.03.2026.
//

#ifndef QUANTENGINE_STOCHASTICPROCESS_HPP
#define QUANTENGINE_STOCHASTICPROCESS_HPP
#include "MarketData.hpp"
#include <memory>

class StochasticProcess {
public:
    StochasticProcess() = delete;
    explicit StochasticProcess(MarketData data) : data_(std::move(data)){}

    virtual ~StochasticProcess() = default;
    virtual double drift(double t, double s) = 0;
    virtual double diffusion(double t, double s) = 0;
    virtual double step(double t, double s, double dt, double dW) = 0;
    const MarketData& data() const {return data_;}


private:
    MarketData data_;

};


#endif //QUANTENGINE_STOCHASTICPROCESS_HPP
