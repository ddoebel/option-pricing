/**
 * @file BlackScholesClosedFormEngine.cpp
 * @brief Black–Scholes closed-form pricing (calls, puts, cash-or-nothing digital).
 */

#include "BlackScholesClosedFormEngine.hpp"
#include "Instrument.hpp"
#include "Payoff.hpp"
#include <cmath>
#include <stdexcept>

namespace {

double norm_cdf(double x) {
    return 0.5 * (1.0 + std::erf(x / std::sqrt(2.0)));
}

} // namespace

double BlackScholesClosedFormEngine::calculate(const Instrument &instrument) const {
    if (instrument.exerciseType() != Exercise::Type::European) {
        throw std::invalid_argument("BlackScholesClosedFormEngine: European exercise only");
    }

    const double T = instrument.maturity();
    const MarketData &md = process_->data();
    const double S = md.spot();
    double K = instrument.payoff().strike();
    const PayoffKind pk = instrument.payoff().kind();

    if (T <= 0.0) {
        return instrument.payoff()(S);
    }

    const double r = md.yield_curve().zeroRate(T);
    const double sigma = md.volatility_surface().sigma(K, T);
    if (sigma <= 0.0) {
        throw std::invalid_argument("BlackScholesClosedFormEngine: volatility must be positive");
    }

    const double disc = md.yield_curve().discount(T);
    const double sqrtT = std::sqrt(T);
    const double sig_sqrtT = sigma * sqrtT;

    if (sig_sqrtT < 1e-15) {
        const double forward = S * std::exp(r * T);
        switch (pk) {
        case PayoffKind::Call:
            return disc * std::max(0.0, forward - K);
        case PayoffKind::Put:
            return disc * std::max(0.0, K - forward);
        case PayoffKind::Digital:
            return (forward > K) ? disc : 0.0;
        }
    }

    const double d1 = (std::log(S / K) + (r + 0.5 * sigma * sigma) * T) / sig_sqrtT;
    const double d2 = d1 - sig_sqrtT;

    switch (pk) {
    case PayoffKind::Call:
        return S * norm_cdf(d1) - K * disc * norm_cdf(d2);
    case PayoffKind::Put:
        return K * disc * norm_cdf(-d2) - S * norm_cdf(-d1);
    case PayoffKind::Digital:
        return disc * norm_cdf(d2);
    }
    throw std::logic_error("BlackScholesClosedFormEngine: unhandled PayoffKind");
}
