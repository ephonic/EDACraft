#include <fstream>
#include <map>
#include <cstdlib>



using namespace std;


void dump_graph(map<int, map<int, double> >& g, int num_ports, int* partition, int n, int num_blocks, int* block_label)
{
  char filename[30];
  int k,i;

  ofstream dot_file;

  for(k = 0; k < num_blocks; ++k)
    {
      sprintf(&filename[0], "graph_%d.dot", k);
  
      dot_file.open(filename);
      
      dot_file << "graph G {" << endl;

      map<int, double>::iterator iter;

      for(i = 0; i < n; ++i)
	{

	  if(i < num_ports && block_label[i] == k)
	    dot_file << i << "[color=red];" << endl;
	  else
	    if(block_label[i] == k)
	      dot_file << i << "[label=" << partition[i] << ", shape = box];" << endl;

	  for(iter = g[i].begin(); iter != g[i].end(); ++iter)
	    {
	      if(i < iter->first && block_label[iter->first] == k)
		dot_file << i << " -- " << iter->first << ";" << endl;
	    }
      
	}

      dot_file << "}" << endl;
      dot_file.close();
    }
}
