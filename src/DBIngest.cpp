//
// Created by David Doebel  on 13.03.2026.
//

#include "DBIngest.hpp"

#include <iostream>

// Queries
// Query for selecting the volatility surface parameters
std::string vol_surface_query = ""




//




bool DBIngest::connect() {
    connection_ = pqxx::connection("dbname=options_db user=quant_user port = 5432 host = localhost password = strong_password" );

    if(connection_.is_open()) {
        std::cout << "Connected\n";
        return true;
    }
    std::cout << "Not connected\n";
    return false;
}

bool DBIngest::disconnect() {
    connection_.close();
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

}

bool DBIngest::update(YieldCurve &yield_curve) {
}
