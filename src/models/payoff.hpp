//
// Created by David Doebel  on 03.03.2026.
//

#ifndef OPTION_PRICING_PAYOFF_HPP
#define OPTION_PRICING_PAYOFF_HPP
class Payoff {
public:
    virtual double operator()(double ST) const = 0;
    virtual ~Payoff() = default;
};

class CallPayoff : public Payoff {
public:
    CallPayoff(double K) : K_(K) {}

    double operator()(double ST) const override;
private:
    double K_;
};
#endif //OPTION_PRICING_PAYOFF_HPP