/**
 * @file RandomGenerator.hpp
 * @brief Random numbers for Monte Carlo (Gaussian draws).
 */

#ifndef QUANTENGINE_RANDOMGENERATOR_HPP
#define QUANTENGINE_RANDOMGENERATOR_HPP
#include <random>

/** @brief Interface for standard normal variates. */
class RandomGenerator {
public:
    RandomGenerator() = default;
    virtual ~RandomGenerator() = default;
    virtual double nextGaussian() = 0;
    virtual std::vector<double> nextGaussianVector(std::size_t n) = 0;
};

/** @brief @c std::mt19937 with normal distribution. */
class MersenneTwister : public RandomGenerator {
public:
    MersenneTwister() = default;
    double nextGaussian() override;
    std::vector<double> nextGaussianVector(std::size_t n) override;
private:
    std::mt19937 generator_;
    std::normal_distribution<> distr_ {0.0, 1.0};
};


#endif //QUANTENGINE_RANDOMGENERATOR_HPP