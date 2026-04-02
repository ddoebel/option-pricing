/**
 * @file FlatVolatilitySurface.hpp
 * @brief Constant implied volatility surface.
 */
#ifndef QUANTENGINE_FLATVOLATILITYSURFACE_HPP
#define QUANTENGINE_FLATVOLATILITYSURFACE_HPP
#include "VolatilitySurface.hpp"

/**
 * @brief @f$\sigma(K,T)\equiv\sigma_0@f$.
 */
class FlatVolatilitySurface : public VolatilitySurface {
public:
    explicit FlatVolatilitySurface(double sigma = 0.2) : sigma_(sigma) {}

    double sigma(double K, double T) const override {return sigma_;}

private:
    double sigma_;
};
#endif
