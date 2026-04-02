/**
 * @file FlatYieldCurve.hpp
 * @brief Constant zero rate yield curve.
 */
#ifndef QUANTENGINE_FLATYIELDCURVE_HPP
#define QUANTENGINE_FLATYIELDCURVE_HPP
#include "YieldCurve.hpp"
#include <cmath>

/**
 * @brief @f$P(t)=e^{-r t}@f$, @f$f(t)\equiv r@f$.
 */
class FlatYieldCurve : public YieldCurve{
public:
    explicit FlatYieldCurve(double rate = 0.01) : rate_(rate) {}

    double discount(double t) const override {return std::exp(-rate_ * t); };
    double zeroRate(double t) const override {return rate_; }
private:
    double rate_ = 0.01;
};
#endif
