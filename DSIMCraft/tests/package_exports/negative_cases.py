"""Language boundaries; no-import/wrong-source are stricter than VCS W-2024.09."""
p = 'package p;parameter int X=3,Y=4;typedef logic[2:0] T;endpackage '
q = 'package q;parameter int X=7;endpackage '
negatives = {
 'unused_wildcard': (p+'package a;import p::*;export p::*;endpackage module top;integer v;initial v=a::X;endmodule', 'package member not found'),
 'unused_all': (p+'package a;import p::*;export *::*;endpackage module top;integer v;initial v=a::X;endmodule', 'package member not found'),
 'unused_sibling': (p+'package a;import p::*;export p::*;parameter Z=X;endpackage module top;integer v;initial v=a::Y;endmodule', 'package member not found'),
 'private_import': (p+'package a;import p::X;endpackage module top;integer v;initial v=a::X;endmodule', 'package member not found'),
 'no_import': (p+'package a;export p::X;endpackage module top;endmodule', 'export requires an import'),
 'wrong_source': (p+'package a;import p::X;export p::X;endpackage package b;import a::X;export p::X;endpackage module top;endmodule', 'export requires an import'),
 'wrong_member': (p+'package a;import p::*;export p::absent;endpackage module top;endmodule', 'package member not found in export'),
 'local_shadow': (p+'package a;import p::*;parameter X=8;export p::X;endpackage module top;endmodule', 'export conflicts with declaration'),
 'local_after': (p+'package a;import p::*;export p::X;parameter X=8;endpackage module top;endmodule', 'redefined'),
 'forward_local': (p+'package a;export p::X;parameter X=8;import p::*;endpackage module top;endmodule', 'export conflicts with declaration'),
 'used_ambiguous': (p+q+'package a;import p::*;import q::*;parameter K=X;export p::X;endpackage module top;endmodule', 'ambiguous wildcard'),
 'used_conflict': (p+q+'package a;import p::*;parameter K=X;import q::*;export q::X;endpackage module top;endmodule', 'export conflicts with declaration'),
 'explicit_conflict': (p+q+'package a;import p::X;import q::X;export p::*;endpackage module top;endmodule', 'conflicting explicit'),
 'module_scope': (p+'module top;import p::*;export p::X;endmodule', 'syntax error'),
 'interface_scope': (p+'interface bus;import p::*;export p::X;endinterface module top;bus b();endmodule', 'require package scope'),
 'block_scope': (p+'module top;initial begin import p::*;export p::X;end endmodule', 'syntax error'),
 'unit_scope': (p+'export p::X;module top;endmodule', 'syntax error'),
}
