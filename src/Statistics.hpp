//
// Created by David Doebel  on 06.03.2026.
//

#ifndef QUANTENGINE_STATISTICS_HPP
#define QUANTENGINE_STATISTICS_HPP
#include <vector>


class Statistics {
public:
    Statistics() : moments_({0., 0., 0.}), n(0), max_(0.), min_(0.) {}
    void dump(double value);
    void clear();
    double mean();
    double variance();
    double standardDeviation();
    double skewness();
    double max();
    double min();
    double sum();
    double count();
private:
    std::vector<double> moments_;
    std::size_t n;
    double max_, min_;
};


#endif //QUANTENGINE_STATISTICS_HPP
