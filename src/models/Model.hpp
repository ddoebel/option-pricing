//
// Created by David Doebel  on 05.03.2026.
//

#ifndef QUANTENGINE_MODEL_HPP
#define QUANTENGINE_MODEL_HPP


class Model {
public:
    Model() = default;
    virtual ~Model() = 0;
    [[nodiscard]] virtual double terminal_price(double Z) const = 0;
    [[nodiscard]] virtual double discount() const = 0;
};


#endif //QUANTENGINE_MODEL_HPP