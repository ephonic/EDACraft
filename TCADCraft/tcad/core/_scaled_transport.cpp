#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "boltzmann_scaled_transport.h"
namespace {
bool strings(PyObject* o,size_t maximum,std::vector<std::string>& out) {
    if(!PyList_CheckExact(o) && !PyTuple_CheckExact(o)){PyErr_SetString(PyExc_ValueError,"scaled transport list or tuple required");return false;}
    const auto n=PySequence_Size(o);if(n<0 || size_t(n)>maximum){PyErr_SetString(PyExc_ValueError,"scaled transport token budget");return false;}
    for(Py_ssize_t i=0;i<n;++i) {
        auto* item=PyList_CheckExact(o)?PyList_GET_ITEM(o,i):PyTuple_GET_ITEM(o,i);Py_ssize_t size=0;
        if(!PyUnicode_CheckExact(item)){PyErr_SetString(PyExc_ValueError,"scaled transport string tokens required");return false;}
        const char* s=PyUnicode_AsUTF8AndSize(item,&size);if(!s)return false;
        if(size<1 || size>64 || std::string(s,size).find('\0')!=std::string::npos){PyErr_SetString(PyExc_ValueError,"scaled transport short tokens required");return false;}
        out.emplace_back(s,size);
    }
    return true;
}
template<int Operation> PyObject* call(PyObject*,PyObject* args) {
    constexpr int count=Operation==1?3:4;
    if(PyTuple_GET_SIZE(args)!=count){PyErr_SetString(PyExc_TypeError,"scaled transport argument coverage");return nullptr;}
    try {
        const std::vector<size_t> limits=Operation==0?std::vector<size_t>{25000,8195,8195,8195}:
            Operation==1?std::vector<size_t>{60000,60000,5}:std::vector<size_t>{60000,262144,1,8195};
        std::vector<std::vector<std::string>> v(count);
        for(int i=0;i<count;++i)if(!strings(PyTuple_GET_ITEM(args,i),limits[i],v[i]))return nullptr;
        std::vector<std::string> result;
        if constexpr(Operation==0)result=tcad::native_mb_scaled_endpoint_raw(v[0],v[1],v[2],v[3]);
        if constexpr(Operation==1)result=tcad::native_mb_scaled_face_raw(v[0],v[1],v[2]);
        if constexpr(Operation==2)result=tcad::native_mb_scaled_cell_raw(v[0],v[1],v[2],v[3]);
        auto* list=PyList_New(result.size());if(!list)return nullptr;
        for(size_t i=0;i<result.size();++i){auto* s=PyUnicode_FromStringAndSize(result[i].data(),result[i].size());if(!s){Py_DECREF(list);return nullptr;}PyList_SET_ITEM(list,i,s);}
        return list;
    }catch(const std::bad_alloc&){return PyErr_NoMemory();}
     catch(const std::exception& e){PyErr_SetString(PyExc_ValueError,e.what());return nullptr;}
}
PyMethodDef methods[]={
    {"native_mb_scaled_endpoint_raw",call<0>,METH_VARARGS,"Exact endpoint materialization."},
    {"native_mb_scaled_face_raw",call<1>,METH_VARARGS,"Full-density scaled moments with division evidence."},
    {"native_mb_scaled_cell_raw",call<2>,METH_VARARGS,"Scaled conservative transport state and exact clock."},
    {nullptr,nullptr,0,nullptr}};
PyModuleDef module={PyModuleDef_HEAD_INIT,"_scaled_transport","Optional binary113 scaled MB transport.",-1,methods};
}
PyMODINIT_FUNC PyInit__scaled_transport(){
    if(tcad::real_mantissa_bits()!=113){PyErr_SetString(PyExc_ImportError,"scaled transport requires binary113");return nullptr;}
    auto* m=PyModule_Create(&module);if(!m)return nullptr;
    if(PyModule_AddIntConstant(m,"precision_bits",113)<0){Py_DECREF(m);return nullptr;}return m;
}
