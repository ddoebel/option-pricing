//
// Created by David Doebel  on 05.03.2026.
//

#ifndef QUANTENGINE_STOCHASTICPROCESS_HPP
#define QUANTENGINE_STOCHASTICPROCESS_HPP
#include "MarketData.hpp"
#include <memory>

class StochasticProcess {
public:
    StochasticProcess() = default;
    StochasticProcess(std::unique_ptr<MarketData> data) : data_(std::move(data)){}

    virtual ~StochasticProcess() = default;
    virtual double drift(double t, double s) = 0;
    virtual double diffusion(double t, double s) = 0;
    virtual double step(double t, double s, double dt, double dW) = 0;
    MarketData& data() const {return *data_;}


private:
    std::shared_ptr<MarketData> data_;

};


#endif //QUANTENGINE_STOCHASTICPROCESS_HPP