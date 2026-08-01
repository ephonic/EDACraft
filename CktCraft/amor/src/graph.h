#ifndef GRAPH_H_
#define GRAPH_H_

/**
 * @file
 * Header file for the graph.
 * @author Yang Fan
 * @date Dec. 10, 2008
 */

#include <boost/config.hpp>
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/connected_components.hpp>

using namespace boost;


/** definition of a boost graph. */
typedef adjacency_list <vecS, vecS, undirectedS> graph_t;


#endif

