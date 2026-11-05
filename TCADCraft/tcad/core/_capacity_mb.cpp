#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "boltzmann_capacity_endpoint_collision.h"
namespace {
std::vector<std::string> strings(PyObject* o,size_t maximum) {
    if(!PyList_CheckExact(o) && !PyTuple_CheckExact(o))throw std::invalid_argument("capacity string sequence required");
    const auto n=PySequence_Size(o);if(n<0 || size_t(n)>maximum)throw std::invalid_argument("capacity token budget");
    std::vector<std::string> out;
    for(Py_ssize_t i=0;i<n;++i){auto* x=PyList_CheckExact(o)?PyList_GET_ITEM(o,i):PyTuple_GET_ITEM(o,i);Py_ssize_t length=0;
        if(!PyUnicode_CheckExact(x))throw std::invalid_argument("capacity string token required");
        const char* s=PyUnicode_AsUTF8AndSize(x,&length);if(!s)throw std::invalid_argument("capacity UTF8 required");
        if(length<1 || length>64 || std::string(s,length).find('\0')!=std::string::npos)throw std::invalid_argument("capacity short token required");out.emplace_back(s,length);}
    return out;
}
template<bool Collision> PyObject* call(PyObject*,PyObject* args){try{
    constexpr int size=Collision?2:3;if(PyTuple_GET_SIZE(args)!=size){PyErr_SetString(PyExc_TypeError,"capacity argument coverage");return nullptr;}
    std::vector<std::string> r;
    if constexpr(Collision)r=tcad::native_mb_capacity_endpoint_collision_raw(strings(PyTuple_GET_ITEM(args,0),60000),strings(PyTuple_GET_ITEM(args,1),6));
    else {auto op=strings(PyTuple_GET_ITEM(args,0),1);if(op.size()!=1)throw std::invalid_argument("one capacity operation required");r=tcad::native_mb_capacity_arithmetic_raw(op[0],strings(PyTuple_GET_ITEM(args,1),8195),strings(PyTuple_GET_ITEM(args,2),8195));}
    auto* out=PyList_New(r.size());if(!out)return nullptr;for(size_t i=0;i<r.size();++i){auto* s=PyUnicode_FromStringAndSize(r[i].data(),r[i].size());if(!s){Py_DECREF(out);return nullptr;}PyList_SET_ITEM(out,i,s);}return out;
}catch(const std::bad_alloc&){return PyErr_NoMemory();}catch(const std::exception& e){PyErr_SetString(PyExc_ValueError,e.what());return nullptr;}}
PyMethodDef methods[]={{"arithmetic",call<false>,METH_VARARGS,"Capacity-checked exact arithmetic."},{"collision",call<true>,METH_VARARGS,"Capacity-checked fixed-tau collision graph."},{nullptr,nullptr,0,nullptr}};
PyModuleDef module={PyModuleDef_HEAD_INIT,"_capacity_mb",nullptr,-1,methods};
}
PyMODINIT_FUNC PyInit__capacity_mb(){if(tcad::real_mantissa_bits()!=113){PyErr_SetString(PyExc_ImportError,"binary113 required");return nullptr;}return PyModule_Create(&module);}
