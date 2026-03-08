//
// Created by David Doebel  on 05.03.2026.
//

#ifndef QUANTENGINE_EXERCISE_HPP
#define QUANTENGINE_EXERCISE_HPP
#include <vector>

class Exercise {
public:
    Exercise() = default;
    virtual ~Exercise() = default;
    enum class Type {
        European,
        American,
        Bermudan
    };

    virtual Type type() const = 0;
protected:
    std::vector<double> exercise_times_;

};

class EuropeanExercise : public Exercise {
    EuropeanExercise() : type_(Type::European) {};
    EuropeanExercise(double maturity) : type_(Type::European){
        exercise_times_.push_back(maturity);
    }
    ~EuropeanExercise() override = default;
    [[nodiscard]] Type type() const override {
        return type_;
    }
private:
    Type type_;
};

class AmericanExercise : public Exercise{
    AmericanExercise() : type_(Type::American) {};
    AmericanExercise(double maturity) : type_(Type::American) {
        exercise_times_.push_back(0);
        exercise_times_.push_back(maturity);
    }
    [[nodiscard]] Type type() const override {
        return type_;
    }

private:
    Type type_;
};


#endif //QUANTENGINE_EXERCISE_HPP