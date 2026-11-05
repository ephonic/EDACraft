#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "boltzmann_lattice_transport.h"
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
template<int Mode> PyObject* call(PyObject*,PyObject* args){try{
    constexpr int size=Mode==1?2:3;if(PyTuple_GET_SIZE(args)!=size){PyErr_SetString(PyExc_TypeError,"lattice argument coverage");return nullptr;}
    const auto a=strings(PyTuple_GET_ITEM(args,0),60000);std::vector<std::string> r;
    if constexpr(Mode==0)r=tcad::mb_lattice_detail::face(a,strings(PyTuple_GET_ITEM(args,1),60000),strings(PyTuple_GET_ITEM(args,2),5),false);
    if constexpr(Mode==1)r=tcad::mb_lattice_detail::face(a,{},strings(PyTuple_GET_ITEM(args,1),6),true);
    if constexpr(Mode==2)r=tcad::mb_lattice_detail::cell(a,strings(PyTuple_GET_ITEM(args,1),262144),strings(PyTuple_GET_ITEM(args,2),1));
    auto* out=PyList_New(r.size());if(!out)return nullptr;
    for(size_t i=0;i<r.size();++i){auto* s=PyUnicode_FromStringAndSize(r[i].data(),r[i].size());if(!s){Py_DECREF(out);return nullptr;}PyList_SET_ITEM(out,i,s);}return out;
}catch(const std::bad_alloc&){return PyErr_NoMemory();}catch(const std::exception& e){PyErr_SetString(PyExc_ValueError,e.what());return nullptr;}}
PyMethodDef methods[]={{"face",call<0>,METH_VARARGS,"Frozen Fourier lattice heat flux."},{"bath",call<1>,METH_VARARGS,"Maintained thermal bath flux."},{"cell",call<2>,METH_VARARGS,"Lattice increment with carrier-coordinate compensation."},{nullptr,nullptr,0,nullptr}};
PyModuleDef module={PyModuleDef_HEAD_INIT,"_lattice_mb",nullptr,-1,methods};
}
PyMODINIT_FUNC PyInit__lattice_mb(){if(tcad::real_mantissa_bits()!=113){PyErr_SetString(PyExc_ImportError,"binary113 required");return nullptr;}return PyModule_Create(&module);}
