//
// Created by David Doebel  on 07.03.2026.
//
#ifndef QUANTENGINE_FAKEMARKETDATA_HPP
#define QUANTENGINE_FAKEMARKETDATA_HPP
#include "MarketData.hpp"
#include "FlatYieldCurve.hpp"
#include "FlatVolatilitySurface.hpp"

class FakeMarketData : public MarketData {
public:
    FakeMarketData() = default;

    FakeMarketData(const FakeMarketData &other)
         {
    }

    FakeMarketData(FakeMarketData &&other) noexcept
        {
    }

    FakeMarketData & operator=(const FakeMarketData &other) {
        return *this;
    }

    FakeMarketData & operator=(FakeMarketData &&other) noexcept {
        return *this;
    }

    double spot() const {return 100.0;}
    YieldCurve& yield_curve(){return *yieldCurve_; };
    VolatilitySurface& volatility_surface(){return *volatilitySurface_; };

private:
    std::unique_ptr<FlatYieldCurve> yieldCurve_ = std::make_unique<FlatYieldCurve>();
    std::unique_ptr<FlatVolatilitySurface> volatilitySurface_ = std::make_unique<FlatVolatilitySurface>();
};
#endif