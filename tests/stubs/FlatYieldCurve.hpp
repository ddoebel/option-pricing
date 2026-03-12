//
// Created by David Doebel  on 07.03.2026.
//
#ifndef QUANTENGINE_FLATYIELDCURVE_HPP
#define QUANTENGINE_FLATYIELDCURVE_HPP
#include "YieldCurve.hpp"
#include <cmath>

class FlatYieldCurve : public YieldCurve{
public:
    explicit FlatYieldCurve(double rate = 0.01) : rate_(rate) {}

    double discount(double t) const override {return std::exp(-rate_ * t); };
    double zeroRate(double t) const override {return rate_; }
private:
    double rate_ = 0.01;
};
#endif
