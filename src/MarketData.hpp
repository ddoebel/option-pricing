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
    MarketData() = default;

    MarketData(double spot, std::unique_ptr<YieldCurve> yield_curve,
         std::unique_ptr<VolatilitySurface> volatility_surface)
        : spot_(spot),
          yield_curve_(std::move(yield_curve)),
          volatility_surface_(std::move(volatility_surface)) {
    }

    double spot() const;
    YieldCurve& yield_curve();
    VolatilitySurface& volatility_surface();

private:
    double spot_;
    std::unique_ptr<YieldCurve> yield_curve_;
    std::unique_ptr<VolatilitySurface> volatility_surface_;
};


#endif //QUANTENGINE_MARKETDATA_HPP