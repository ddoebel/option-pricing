/**
 * @file StochasticProcess.hpp
 * @brief Interface for SDE drift, diffusion, and time stepping.
 */

#ifndef QUANTENGINE_STOCHASTICPROCESS_HPP
#define QUANTENGINE_STOCHASTICPROCESS_HPP
#include "MarketData.hpp"
#include <memory>

/**
 * @brief Stochastic model for the underlying, driven by @ref MarketData.
 */
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
