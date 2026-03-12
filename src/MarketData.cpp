//
// Created by David Doebel  on 06.03.2026.
//

#include "MarketData.hpp"

double MarketData::spot() const { return spot_; }
const YieldCurve& MarketData::yield_curve() const { return *yield_curve_; }
const VolatilitySurface& MarketData::volatility_surface() const { return *volatility_surface_; }
