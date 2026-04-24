/*
 * DPI-C bridge for SHA3-256 Python reference model.
 *
 * Compiles to a shared library (libdpi_sha3.so / .dylib) and is loaded
 * by the SV simulator at runtime.
 */

#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int py_initialized = 0;

static void py_init_once(void)
{
    if (!py_initialized) {
        Py_Initialize();
        py_initialized = 1;
    }
}

void dpi_sha3_256(unsigned long long block[17], int len, unsigned long long hash[4])
{
    py_init_once();
    PyGILState_STATE gstate = PyGILState_Ensure();

    /* Ensure project root is on sys.path so rtlgen.dpi_runtime can be found. */
    PyRun_SimpleString("import sys; sys.path.insert(0, '/Users/yangfan/rtlgen')");

    /* Reconstruct the little-endian byte vector from the 17 64-bit lanes. */
    unsigned char *msg = (unsigned char *)malloc(135);
    if (!msg) {
        PyGILState_Release(gstate);
        return;
    }
    memset(msg, 0, 135);
    for (int i = 0; i < 17; i++) {
        unsigned long long w = block[i];
        for (int b = 0; b < 8; b++) {
            msg[i * 8 + b] = (unsigned char)((w >> (b * 8)) & 0xFFULL);
        }
    }

    PyObject *py_bytes = PyBytes_FromStringAndSize((const char *)msg, len);
    free(msg);
    if (!py_bytes) {
        fprintf(stderr, "[DPI] PyBytes_FromStringAndSize failed\n");
        PyGILState_Release(gstate);
        return;
    }

    PyObject *py_mod = PyImport_ImportModule("rtlgen.dpi_runtime");
    if (!py_mod) {
        fprintf(stderr, "[DPI] Failed to import rtlgen.dpi_runtime\n");
        PyErr_Print();
        Py_DECREF(py_bytes);
        PyGILState_Release(gstate);
        return;
    }

    PyObject *py_func = PyObject_GetAttrString(py_mod, "dpi_sha3_256");
    if (!py_func || !PyCallable_Check(py_func)) {
        fprintf(stderr, "[DPI] dpi_sha3_256 not found or not callable in rtlgen.dpi_runtime\n");
        PyErr_Print();
        Py_XDECREF(py_func);
        Py_DECREF(py_mod);
        Py_DECREF(py_bytes);
        PyGILState_Release(gstate);
        return;
    }

    PyObject *py_args = PyTuple_Pack(1, py_bytes);
    PyObject *py_ret = PyObject_CallObject(py_func, py_args);

    if (!py_ret) {
        fprintf(stderr, "[DPI] Call to dpi_sha3_256 failed\n");
        PyErr_Print();
        Py_XDECREF(py_args);
        Py_DECREF(py_func);
        Py_DECREF(py_mod);
        PyGILState_Release(gstate);
        return;
    }

    char *digest = NULL;
    Py_ssize_t digest_len = 0;
    if (PyBytes_AsStringAndSize(py_ret, &digest, &digest_len) < 0) {
        fprintf(stderr, "[DPI] PyBytes_AsStringAndSize failed\n");
        PyErr_Print();
        Py_DECREF(py_ret);
        Py_XDECREF(py_args);
        Py_DECREF(py_func);
        Py_DECREF(py_mod);
        PyGILState_Release(gstate);
        return;
    }

    memset(hash, 0, 4 * sizeof(unsigned long long));
    for (int i = 0; i < 4 && (i * 8) < digest_len; i++) {
        unsigned long long w = 0;
        for (int b = 0; b < 8; b++) {
            w |= ((unsigned long long)(unsigned char)digest[i * 8 + b]) << (b * 8);
        }
        hash[i] = w;
    }

    Py_DECREF(py_ret);
    Py_XDECREF(py_args);
    Py_DECREF(py_func);
    Py_DECREF(py_mod);
    /* py_bytes is owned by py_args and already released when py_args was freed */
    PyGILState_Release(gstate);
}
