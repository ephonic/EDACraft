#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "boltzmann_accounted_rounding.h"
namespace {
std::vector<std::string> strings(PyObject* o,size_t maximum) {
    if(!PyList_CheckExact(o) && !PyTuple_CheckExact(o))throw std::invalid_argument("lattice string sequence required");
    const auto n=PySequence_Size(o);if(n<0 || size_t(n)>maximum)throw std::invalid_argument("lattice token budget");
    std::vector<std::string> out;
    for(Py_ssize_t i=0;i<n;++i){auto* x=PyList_CheckExact(o)?PyList_GET_ITEM(o,i):PyTuple_GET_ITEM(o,i);Py_ssize_t length=0;
        if(!PyUnicode_CheckExact(x))throw std::invalid_argument("lattice string token required");
        const char* s=PyUnicode_AsUTF8AndSize(x,&length);if(!s)throw std::invalid_argument("lattice UTF8 required");
        if(length<1 || length>64 || std::string(s,length).find('\0')!=std::string::npos)throw std::invalid_argument("lattice short token required");out.emplace_back(s,length);}
    return out;
}
PyObject* call(PyObject*,PyObject* args){try{
    if(PyTuple_GET_SIZE(args)!=1){PyErr_SetString(PyExc_TypeError,"accounted rounding argument coverage");return nullptr;}
    const auto r=tcad::mb_accounted_rounding_detail::endpoint(strings(PyTuple_GET_ITEM(args,0),60000));
    auto* out=PyList_New(r.size());if(!out)return nullptr;
    for(size_t i=0;i<r.size();++i){auto* s=PyUnicode_FromStringAndSize(r[i].data(),r[i].size());if(!s){Py_DECREF(out);return nullptr;}PyList_SET_ITEM(out,i,s);}return out;
}catch(const std::bad_alloc&){return PyErr_NoMemory();}catch(const std::exception& e){PyErr_SetString(PyExc_ValueError,e.what());return nullptr;}}
PyMethodDef methods[]={{"endpoint",call,METH_VARARGS,"RN113 endpoint with all exact coordinate differences saved."},{nullptr,nullptr,0,nullptr}};
PyModuleDef module={PyModuleDef_HEAD_INIT,"_accounted_rounding_mb",nullptr,-1,methods};
}
PyMODINIT_FUNC PyInit__accounted_rounding_mb(){if(tcad::real_mantissa_bits()!=113){PyErr_SetString(PyExc_ImportError,"binary113 required");return nullptr;}return PyModule_Create(&module);}
