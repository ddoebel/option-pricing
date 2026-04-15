/**
 * @file Pybind.cpp
 * @brief pybind11 module @c qengine exposing @ref BSWrapper::bs_price_wrapper overloads.
 */

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

#include "BSWrapper.hpp"

namespace py = pybind11;

namespace {

std::vector<double> to_vector_double(const py::array_t<double> &a) {
    py::buffer_info info = a.request();
    if (info.ndim != 1) {
        throw std::runtime_error("expected 1-D ndarray for S, K, T, r, sigma");
    }
    const auto *p = static_cast<const double *>(info.ptr);
    const ssize_t n = info.shape[0];
    return std::vector<double>(p, p + n);
}

std::vector<bool> to_vector_bool_1d(const py::array_t<bool> &a) {
    py::buffer_info info = a.request();
    if (info.ndim != 1) {
        throw std::runtime_error("expected 1-D ndarray for is_call");
    }
    if (info.itemsize != 1) {
        throw std::runtime_error("is_call: expected a boolean ndarray (dtype=bool)");
    }
    const ssize_t n = info.shape[0];
    const auto *p = static_cast<const std::uint8_t *>(info.ptr);
    std::vector<bool> out(static_cast<size_t>(n));
    for (ssize_t i = 0; i < n; ++i) {
        out[static_cast<size_t>(i)] = (p[i] != 0);
    }
    return out;
}

void check_same_length(size_t n, size_t k, const char *name) {
    if (n != k) {
        throw std::runtime_error(std::string("length mismatch for ") + name);
    }
}

} // namespace

PYBIND11_MODULE(qengine, m) {
    m.doc() = "Binding for the Black Scholes model";

    m.def(
        "bs_price",
        [](double S, double K, double T, double r, double sigma, bool is_call) {
            return BSWrapper::bs_price_wrapper(S, K, T, r, sigma, is_call);
        },
        py::arg("S"), py::arg("K"), py::arg("T"), py::arg("r"), py::arg("sigma"), py::arg("is_call"));

    m.def(
        "bs_price",
        [](py::array_t<double> S, py::array_t<double> K, py::array_t<double> T, py::array_t<double> r,
            py::array_t<double> sigma, py::array_t<bool> is_call) {
            std::vector<double> vS = to_vector_double(S);
            std::vector<double> vK = to_vector_double(K);
            std::vector<double> vT = to_vector_double(T);
            std::vector<double> vr = to_vector_double(r);
            std::vector<double> vsig = to_vector_double(sigma);
            std::vector<bool> vC = to_vector_bool_1d(is_call);
            const size_t n = vS.size();
            check_same_length(n, vK.size(), "K");
            check_same_length(n, vT.size(), "T");
            check_same_length(n, vr.size(), "r");
            check_same_length(n, vsig.size(), "sigma");
            check_same_length(n, vC.size(), "is_call");
            return BSWrapper::batch_bs_price_wrapper(vS, vK, vT, vr, vsig, vC);
        },
        py::arg("S"), py::arg("K"), py::arg("T"), py::arg("r"), py::arg("sigma"), py::arg("is_call"));

    m.def(
        "bs_price",
        [](const std::vector<double> &S, const std::vector<double> &K, const std::vector<double> &T,
            const std::vector<double> &r, const std::vector<double> &sigma, const std::vector<bool> &is_call) {
            return BSWrapper::batch_bs_price_wrapper(S, K, T, r, sigma, is_call);
        },
        py::arg("S"), py::arg("K"), py::arg("T"), py::arg("r"), py::arg("sigma"), py::arg("is_call"));
}
