#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "boltzmann_scaled_powerlaw.h"

namespace {
bool strings(PyObject* obj, size_t maximum, std::vector<std::string>& out) {
    if (!PyList_CheckExact(obj) && !PyTuple_CheckExact(obj)) {
        PyErr_SetString(PyExc_ValueError, "scaled native input must be a list or tuple"); return false;
    }
    const auto n=PySequence_Size(obj);
    if (n<0 || static_cast<size_t>(n)>maximum) {
        PyErr_SetString(PyExc_ValueError, "scaled native input token budget exceeded"); return false;
    }
    out.reserve(n);
    for (Py_ssize_t i=0;i<n;++i) {
        PyObject* item=PyList_CheckExact(obj)?PyList_GET_ITEM(obj,i):PyTuple_GET_ITEM(obj,i);
        Py_ssize_t size=0;
        if (!PyUnicode_CheckExact(item)) {
            PyErr_SetString(PyExc_ValueError, "scaled native string tokens required"); return false;
        }
        const char* raw=PyUnicode_AsUTF8AndSize(item,&size);
        if (!raw) return false;
        if (size<1 || size>64 || std::string(raw,size).find('\0')!=std::string::npos) {
            PyErr_SetString(PyExc_ValueError, "scaled native short nonempty tokens required"); return false;
        }
        out.emplace_back(raw,size);
    }
    return true;
}
PyObject* powerlaw(PyObject*,PyObject* args) {
    PyObject *endpoint,*command,*clock;
    if (!PyArg_ParseTuple(args,"OOO",&endpoint,&command,&clock)) return nullptr;
    try {
        std::vector<std::string> a,b,c;
        if (!strings(endpoint,25000,a) || !strings(command,18,b) || !strings(clock,1,c)) return nullptr;
        auto raw=tcad::native_mb_scaled_powerlaw_raw(a,b,c);
        PyObject* result=PyList_New(raw.size()); if (!result) return nullptr;
        for (size_t i=0;i<raw.size();++i) {
            PyObject* value=PyUnicode_FromStringAndSize(raw[i].data(),raw[i].size());
            if (!value) { Py_DECREF(result); return nullptr; }
            PyList_SET_ITEM(result,i,value);
        }
        return result;
    } catch (const std::bad_alloc&) { return PyErr_NoMemory(); }
      catch (const std::exception& e) { PyErr_SetString(PyExc_ValueError,e.what()); return nullptr; }
}
PyMethodDef methods[]={
    {"native_mb_scaled_powerlaw_raw",powerlaw,METH_VARARGS,"Binary113 scaled nonlinear MB collision; no mutation."},
    {nullptr,nullptr,0,nullptr}
};
PyModuleDef module={PyModuleDef_HEAD_INIT,"_scaled_mb","Scaled MB native extension, separate from the legacy core.",-1,methods};
}
PyMODINIT_FUNC PyInit__scaled_mb() {
    if (tcad::real_mantissa_bits()!=113) {
        PyErr_SetString(PyExc_ImportError,"scaled MB requires binary113"); return nullptr;
    }
    PyObject* m=PyModule_Create(&module); if (!m) return nullptr;
    if (PyModule_AddIntConstant(m,"precision_bits",113)<0) { Py_DECREF(m); return nullptr; }
    return m;
}
