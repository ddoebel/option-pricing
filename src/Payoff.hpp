//
// Created by David Doebel  on 05.03.2026.
//

#ifndef QUANTENGINE_PAYOFF_HPP
#define QUANTENGINE_PAYOFF_HPP


class Payoff {
public:


    Payoff() = default;
    virtual ~Payoff() = default;
    virtual double operator()(double S) = 0;
    virtual double strike() = 0;
};

class CallPayoff : public Payoff {
public:
    CallPayoff() = default;
    CallPayoff(double strike) : strike_(strike) {}
    double operator()(double S) override;
    double strike() override {return strike_;}

private:
    double strike_;
};

class PutPayoff : public Payoff {
public:
    PutPayoff() = default;
    PutPayoff(double strike) : strike_(strike) {}
    double operator()(double S) override;
    double strike() override {return strike_;}
private:
    double strike_;
};

class DigitalPayoff : public Payoff {
    public:
    DigitalPayoff() = default;
    DigitalPayoff(double strike) : strike_(strike) {}
    double operator()(double S) override;
    double strike() override {return strike_;}
private:
    double strike_;
};


#endif //QUANTENGINE_PAYOFF_HPP