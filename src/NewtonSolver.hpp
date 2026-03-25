//
// Created by David Doebel  on 13.03.2026.
//

#ifndef QUANTENGINE_GAUSSSOLVER_HPP
#define QUANTENGINE_GAUSSSOLVER_HPP

#include <functional>

class NewtonSolver {
    template<typename F, typename DFinv, typename T>
    bool solve(F&& func, DFinv&& dfinv,T x0 , double rtol, double atol) {
        T x = x0;
        int i = 0;
        T increment;
        do {
            increment = dfinv(x) * func(x);
            x -= increment;
            ++i;
        } while (i < 1000 && std::abs(increment)/ std::abs(x) > rtol && std::abs(increment) > atol);

    }
};


#endif //QUANTENGINE_GAUSSSOLVER_HPP