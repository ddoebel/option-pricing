//
// Created by David Doebel  on 06.03.2026.
//

#ifndef QUANTENGINE_VOLATILITYSURFACE_HPP
#define QUANTENGINE_VOLATILITYSURFACE_HPP


class VolatilitySurface {
public:
    virtual ~VolatilitySurface() = default;
    virtual double sigma(double K, double T) = 0;
private:

};


#endif //QUANTENGINE_VOLATILITYSURFACE_HPP