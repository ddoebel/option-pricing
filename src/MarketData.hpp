//
// Created by David Doebel  on 06.03.2026.
//

#ifndef QUANTENGINE_MARKETDATA_HPP
#define QUANTENGINE_MARKETDATA_HPP
#include "YieldCurve.hpp"
#include "VolatilitySurface.hpp"
#include <memory>

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
