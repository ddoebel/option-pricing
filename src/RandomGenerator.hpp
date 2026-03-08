//
// Created by David Doebel  on 06.03.2026.
//

#ifndef QUANTENGINE_RANDOMGENERATOR_HPP
#define QUANTENGINE_RANDOMGENERATOR_HPP
#include <random>

class RandomGenerator {
public:
    RandomGenerator() = default;
    virtual ~RandomGenerator() = default;
    virtual double nextGaussian() = 0;
    virtual std::vector<double> nextGaussianVector(std::size_t n) = 0;
};

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