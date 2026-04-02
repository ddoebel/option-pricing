/**
 * @file Exercise.hpp
 * @brief Exercise style (European, American, Bermudan) and exercise times.
 */

#ifndef QUANTENGINE_EXERCISE_HPP
#define QUANTENGINE_EXERCISE_HPP
#include <vector>

/**
 * @brief Describes when the holder may exercise (metadata for pricing engines).
 */
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

/** @brief Single exercise at maturity. */
class EuropeanExercise : public Exercise {
public:
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

/** @brief Continuous American exercise from @f$t=0@f$ to maturity (placeholder grid). */
class AmericanExercise : public Exercise{
public:
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