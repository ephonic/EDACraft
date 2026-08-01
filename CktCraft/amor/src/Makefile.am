abs_top_srcdir = @abs_top_srcdir@
INCLUDES = -I$(abs_top_srcdir)/src -I$(abs_top_srcdir)/src/umfpack 
lib_LIBRARIES = libamor.a
libamor_a_SOURCES = cap.cpp \
	   linear_solver.cpp \
           ckt.cpp \
           eigs.cpp \
           element.cpp \
           amor.cpp \
           node_list.cpp \
           res.cpp \
           unit.cpp \
 	   matrix_util.cpp \
	   dump_dot.cpp \
           subckt.cpp \
           timer.cpp



#hmor_LDADD = -lumfpack -lamd -larpack -lblas -llapack -lgfortran
#hmor_LDADD = $(abs_top_srcdir)/lib/libumfpack.a $(abs_top_srcdir)/lib/libamd.a $(abs_top_srcdir)/lib/libarpack.a $(abs_top_srcdir)/lib/libblas.a $(abs_top_srcdir)/lib/liblapack.a $(abs_top_srcdir)/lib/libgfortran.a
AM_CPPFLAGS = -O2 -DNDEBUG
