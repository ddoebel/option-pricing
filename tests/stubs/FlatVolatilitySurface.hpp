//
// Created by David Doebel  on 07.03.2026.
//
#ifndef QUANTENGINE_FLATVOLATILITYSURFACE_HPP
#define QUANTENGINE_FLATVOLATILITYSURFACE_HPP
#include "VolatilitySurface.hpp"

class FlatVolatilitySurface : public VolatilitySurface {
public:
    explicit FlatVolatilitySurface(double sigma = 0.2) : sigma_(sigma) {}

    double sigma(double K, double T) const override {return sigma_;}

private:
    double sigma_;
};
#endif
