/**
 * @file MarketData.cpp
 * @brief @ref MarketData accessors.
 */

#include "MarketData.hpp"

double MarketData::spot() const { return spot_; }
const YieldCurve& MarketData::yield_curve() const { return *yield_curve_; }
const VolatilitySurface& MarketData::volatility_surface() const { return *volatility_surface_; }
