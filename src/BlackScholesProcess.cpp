//
// Created by David Doebel  on 06.03.2026.
//

#include "BlackScholesProcess.hpp"

double BlackScholesProcess::drift(double t, double s) {
    double r = this->data().yield_curve().zeroRate(t);
    return r * s;
}

double BlackScholesProcess::diffusion(double t, double s) {
    double sigma = this->data().volatility_surface().sigma(s,t);
    return sigma*s;
}

double BlackScholesProcess::step(double t, double s, double dt, double dW) {
    double r = this->data().yield_curve().zeroRate(t);
    double sigma = this->data().volatility_surface().sigma(s,t);
    return s*exp((r-0.5*sigma*sigma)*dt + sigma*sqrt(dt)*dW);
}


