/**
 * @file Payoff.hpp
 * @brief Payoff interface and standard European payoffs (call, put, digital).
 */

#ifndef QUANTENGINE_PAYOFF_HPP
#define QUANTENGINE_PAYOFF_HPP

/**
 * @brief Standard payoff shapes for routing (e.g. analytic vs Monte Carlo).
 */
enum class PayoffKind { Call, Put, Digital };

/**
 * @brief Terminal payoff as a function of spot @f$S_T@f$.
 */
class Payoff {
public:


    Payoff() = default;
    virtual ~Payoff() = default;
    virtual double operator()(double S) = 0;
    virtual double strike() = 0;
    [[nodiscard]] virtual PayoffKind kind() const = 0;
};

/** @brief Standard European call @f$\max(S-K,0)@f$. */
class CallPayoff : public Payoff {
public:
    CallPayoff() = default;
    CallPayoff(double strike) : strike_(strike) {}
    double operator()(double S) override;
    double strike() override {return strike_;}
    [[nodiscard]] PayoffKind kind() const override { return PayoffKind::Call; }

private:
    double strike_;
};

/** @brief Standard European put @f$\max(K-S,0)@f$. */
class PutPayoff : public Payoff {
public:
    PutPayoff() = default;
    PutPayoff(double strike) : strike_(strike) {}
    double operator()(double S) override;
    double strike() override {return strike_;}
    [[nodiscard]] PayoffKind kind() const override { return PayoffKind::Put; }
private:
    double strike_;
};

/** @brief Digital (cash-or-nothing style) payoff @f$1_{S>K}@f$. */
class DigitalPayoff : public Payoff {
    public:
    DigitalPayoff() = default;
    DigitalPayoff(double strike) : strike_(strike) {}
    double operator()(double S) override;
    double strike() override {return strike_;}
    [[nodiscard]] PayoffKind kind() const override { return PayoffKind::Digital; }
private:
    double strike_;
};


#endif //QUANTENGINE_PAYOFF_HPP