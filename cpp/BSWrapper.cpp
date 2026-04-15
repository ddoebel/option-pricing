//
// Created by David Doebel  on 27.03.2026.
//

#include "BSWrapper.hpp"

#include "BlackScholesClosedFormEngine.hpp"
#include "BlackScholesProcess.hpp"
#include "Instrument.hpp"
#include "Option.hpp"
#include "FlatVolatilitySurface.hpp"
#include "FlatYieldCurve.hpp"
#include <cassert>
#include <iostream>

class FlatYieldCurve;

double BSWrapper::bs_price_wrapper(double S, double K, double T, double r, double sigma,
    bool is_call) {
    std::shared_ptr<FlatYieldCurve> flat_curve = std::make_shared<FlatYieldCurve>(r);
    auto flat_vol_surface = std::make_shared<FlatVolatilitySurface>(sigma);
    MarketData data(S,flat_curve, flat_vol_surface);
    std::unique_ptr<BlackScholesProcess> process = std::make_unique<BlackScholesProcess>(data);
    std::unique_ptr<BlackScholesClosedFormEngine> pricing_engine =
        std::make_unique<BlackScholesClosedFormEngine>(std::move(process));
    std::unique_ptr<Payoff> payoff;
    if (is_call)
        payoff = std::make_unique<CallPayoff>(K);
    else payoff = std::make_unique<PutPayoff>(K);
    EuropeanExercise exercise(T);
    VanillaOption option(T,std::make_unique<EuropeanExercise>(exercise),
        std::move(payoff),std::move(pricing_engine));
    return option.price();
}

std::vector<double> BSWrapper::batch_bs_price_wrapper(const std::vector<double> &S, const std::vector<double> &K,
    const std::vector<double> &T, const std::vector<double> &r, const std::vector<double> &sigma,
    const std::vector<bool> &is_call) {
    assert(K.size() == S.size() && K.size() == T.size() && K.size() == r.size() && K.size() ==
        sigma.size() && K.size() == is_call.size());
    std::size_t n = K.size();
    std::vector<double> result(n);
    for (std::size_t i = 0; i < n; ++i) {
        result[i] = bs_price_wrapper(S[i], K[i], T[i], r[i], sigma[i], is_call[i]);
        if (i % 100 == 0)
            std::cout << "i = " << i << " result = " << result[i] << std::endl; // ( i % 1000 == 0)
    }
    return result;
}
