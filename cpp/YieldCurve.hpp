/**
 * @file YieldCurve.hpp
 * @brief Abstract yield curve: discount factors and zero rates.
 */

#ifndef QUANTENGINE_YIELDCURVE_HPP
#define QUANTENGINE_YIELDCURVE_HPP

/**
 * @brief Risk-free rate term structure for discounting and risk-neutral drift.
 */
class YieldCurve {
public:
    YieldCurve() = default;

    YieldCurve(const YieldCurve &other) {
    }

    YieldCurve(YieldCurve &&other) noexcept {
    }

    YieldCurve & operator=(const YieldCurve &other) {
        if (this == &other)
            return *this;
        return *this;
    }

    YieldCurve & operator=(YieldCurve &&other) noexcept {
        if (this == &other)
            return *this;
        return *this;
    }
    virtual ~YieldCurve() = default;
    virtual double discount(double t) const = 0;
    virtual double zeroRate(double t) const = 0;

};


#endif //QUANTENGINE_YIELDCURVE_HPP
