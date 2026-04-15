/**
 * @file DBIngest.cpp
 * @brief Database connection and placeholder update routines.
 */

#include "DBIngest.hpp"

#include <cstdlib>
#include <iostream>
#include <sstream>

bool DBIngest::connect() {
    const char* db_name = std::getenv("DB_NAME");
    const char* db_user = std::getenv("DB_USER");
    const char* db_password = std::getenv("DB_PASSWORD");
    const char* db_host = std::getenv("DB_HOST");
    const char* db_port = std::getenv("DB_PORT");

    std::ostringstream conn_str;
    conn_str
        << "dbname=" << (db_name ? db_name : "options_db")
        << " user=" << (db_user ? db_user : "quant_user")
        << " host=" << (db_host ? db_host : "localhost")
        << " port=" << (db_port ? db_port : "5432")
        << " password=" << (db_password ? db_password : "");

    connection_ = pqxx::connection(conn_str.str());

    if(connection_.is_open()) {
        std::cout << "Connected\n";
        return true;
    }
    std::cout << "Not connected\n";
    return false;
}

bool DBIngest::disconnect() {
    connection_.close();
    return true;
}

bool DBIngest::update(VolatilitySurface &surface) {
    std::string vol_surface_query = "SELECT c.strike, c.expiration_date, q.mid, u.price "
                                    "FROM option_quotes q"
                                    "JOIN option_contracts c "
                                    "ON q.contract_id = c.id "
                                    "JOIN underlying_prices u"
                                    "ON u.underlying_id = c.underlying_id"
                                    "WHERE q.timestamp = ("
                                    "SELECT MAX(timestamp) FROM option_quotes"
                                    ")";
    pqxx::work work(connection_);
    pqxx::result result = work.exec(vol_surface_query);
    for (auto row : result) {
        std::cout << row[0] << " " << row[1] << " " << row[2] << " " << row[3] << std::endl;
    }
    (void)surface;
    return false;
}

bool DBIngest::update(YieldCurve &yield_curve) {
    (void)yield_curve;
    return false;
}
