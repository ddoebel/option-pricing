//
// Created by David Doebel  on 04.03.2026.
//

#ifndef QUANTENGINE_STATS_HPP
#define QUANTENGINE_STATS_HPP
#include <cstddef>
#include <utility>

class Stats {
private:
    size_t n_ = 0;
    double running_sum_ = 0.0;
    double running_square_sum_ = 0.0;

public:
    Stats() = delete;
    void update(double x);
    double mean() const;
    double square_mean() const;
    double variance() const;
    double std_error() const;
    std::pair<double, double> CI() const; // alpha = 5%

};


#endif //QUANTENGINE_STATS_HPP