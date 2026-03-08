//
// Created by David Doebel  on 06.03.2026.
//

#include "MarketData.hpp"

double MarketData::spot() const { return spot_; }
YieldCurve& MarketData::yield_curve() { return *yield_curve_; }
VolatilitySurface& MarketData::volatility_surface() { return *volatility_surface_; }