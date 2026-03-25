//
// Created by David Doebel  on 13.03.2026.
//

#ifndef QUANTENGINE_DBINGEST_HPP
#define QUANTENGINE_DBINGEST_HPP

#include <pqxx/pqxx>

#include "VolatilitySurface.hpp"
#include "YieldCurve.hpp"

class DBIngest {

    bool connect();
    bool disconnect();
    bool update(VolatilitySurface& surface);
    bool update(YieldCurve& yield_curve);
private:
    pqxx::connection connection_;
};


#endif //QUANTENGINE_DBINGEST_HPP