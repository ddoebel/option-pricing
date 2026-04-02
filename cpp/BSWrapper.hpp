/**
 * @file BSWrapper.hpp
 * @brief Black–Scholes vanilla price (closed form; used from Python / implied vol).
 */

#ifndef QUANTENGINE_BSWRAPPER_HPP
#define QUANTENGINE_BSWRAPPER_HPP
#include <vector>

/**
 * @brief Static helpers wrapping scalar and batch pricing.
 */
class BSWrapper {
public:
    BSWrapper() = delete;
    static double bs_price_wrapper(double S, double K, double T, double r, double sigma, bool is_call);
    static std::vector<double> batch_bs_price_wrapper(const std::vector<double>& S, const std::vector<double>& K,
        const std::vector<double>& T, const std::vector<double>& r, const std::vector<double>& sigma,
        const std::vector<bool>& is_call);

};


#endif //QUANTENGINE_BSWRAPPER_HPP