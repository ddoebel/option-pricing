/**
 * @file DBIngest.hpp
 * @brief PostgreSQL helpers to load market objects (work in progress).
 */

#ifndef QUANTENGINE_DBINGEST_HPP
#define QUANTENGINE_DBINGEST_HPP

#include <pqxx/pqxx>

#include "VolatilitySurface.hpp"
#include "YieldCurve.hpp"

/**
 * @brief Connects to Postgres via libpqxx and queries quotes for surface building.
 */
class DBIngest {

    bool connect();
    bool disconnect();
    bool update(VolatilitySurface& surface);
    bool update(YieldCurve& yield_curve);
private:
    pqxx::connection connection_;
};


#endif //QUANTENGINE_DBINGEST_HPP