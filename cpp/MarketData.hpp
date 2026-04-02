/**
 * @file MarketData.hpp
 * @brief Spot, discount curve, and volatility surface bundle.
 */

#ifndef QUANTENGINE_MARKETDATA_HPP
#define QUANTENGINE_MARKETDATA_HPP
#include "YieldCurve.hpp"
#include "VolatilitySurface.hpp"
#include <memory>

/**
 * @brief Immutable snapshot of inputs needed to simulate or price.
 */
class MarketData {
public:
    MarketData() = delete;

    MarketData(double spot, std::shared_ptr<const YieldCurve> yield_curve,
         std::shared_ptr<const VolatilitySurface> volatility_surface)
        : spot_(spot),
          yield_curve_(std::move(yield_curve)),
          volatility_surface_(std::move(volatility_surface)) {
    }

    double spot() const;
    const YieldCurve& yield_curve() const;
    const VolatilitySurface& volatility_surface() const;

private:
    double spot_;
    std::shared_ptr<const YieldCurve> yield_curve_;
    std::shared_ptr<const VolatilitySurface> volatility_surface_;
};


#endif //QUANTENGINE_MARKETDATA_HPP
