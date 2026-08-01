#ifndef DUMP_DOT_H
#define DUMP_DOT_H

/**
 * @file
 * Header file for dumping dot file for analysis (debug mode).
 * @author Yang Fan
 * @date Dec. 10, 2008
 */




/** @addtogroup utility
 *  @{
*/

/** Dump a undirected graph for debug.
  * The generated graph.dot file can then be transformed to pdf file by Graphviz programme*/
void dump_graph(map<int, map<int, double> >& g, int num_ports, int* partition, int n, int num_blocks, int* block_label);

/** @} */

#endif
