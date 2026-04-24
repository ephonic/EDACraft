# Makefile for SHA3-256 DPI bridge
#   make        -> builds libdpi_sha3.so (Linux) or libdpi_sha3.dylib (macOS)
#   make clean  -> removes the shared library

PYTHON ?= python3

CFLAGS  += -fPIC -shared
CFLAGS  += $(shell $(PYTHON)-config --includes)

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    LIBEXT = .dylib
    LDFLAGS += -undefined dynamic_lookup
else
    LIBEXT = .so
    PYTHON_PREFIX ?= $(shell $(PYTHON) -c 'import sys; print(sys.base_prefix)')
    PYTHON_VER    ?= $(shell $(PYTHON) -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    LDFLAGS += -L$(PYTHON_PREFIX)/lib -lpython$(PYTHON_VER)
endif

.PHONY: all clean

all: libdpi_sha3$(LIBEXT)

libdpi_sha3$(LIBEXT): dpi_sha3.c
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<

clean:
	rm -f libdpi_sha3$(LIBEXT)
