//
// Created by David Doebel  on 07.03.2026.
//
#ifndef QUANTENGINE_FLATVOLATILITYSURFACE_HPP
#define QUANTENGINE_FLATVOLATILITYSURFACE_HPP
#include "VolatilitySurface.hpp"

class FlatVolatilitySurface : public VolatilitySurface {
    double sigma(double K, double T) {return 0.2;}
};
#endif