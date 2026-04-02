/**
 * @file VolatilitySurface.hpp
 * @brief Implied volatility as a function of strike and expiry.
 */

#ifndef QUANTENGINE_VOLATILITYSURFACE_HPP
#define QUANTENGINE_VOLATILITYSURFACE_HPP
#include <vector>

/**
 * @brief Local/vol surface @f$\sigma(K,T)@f$ used by simulation.
 */
class VolatilitySurface {
public:
    virtual ~VolatilitySurface() = default;
    virtual double sigma(double K, double T) const = 0;
private:

};

class SVI : public VolatilitySurface {
public:
    SVI() = default;
    SVI(std::vector<double> K, std::vector<double> rho, std::vector<double> S, std::vector<double> T);
};


#endif //QUANTENGINE_VOLATILITYSURFACE_HPP
