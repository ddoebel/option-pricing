//
// Created by David Doebel  on 06.03.2026.
//

#ifndef QUANTENGINE_YIELDCURVE_HPP
#define QUANTENGINE_YIELDCURVE_HPP


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
    virtual double discount(double t) = 0;
    virtual double zeroRate(double t) = 0;

};


#endif //QUANTENGINE_YIELDCURVE_HPP