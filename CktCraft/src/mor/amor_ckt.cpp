#include "amor_comm.h"
#include "amor_ckt.h"
#include "amor_element.h"
#include "amor_cap.h"
#include "amor_res.h"
#include "amor_eigs.h"
#include "amor_dump_dot.h"
#include "amor_timer.h"
#include "amor_subckt_ins.h"
#include "amor_unit.h"
// Boost Graph 替换为 src/mor/graph.h（Graph 类，含 connectedComponents BFS）
#include "graph.h"
#include <algorithm>
#include <cmath>

using namespace rfsim::mor;


using std::string;
using std::cout;
using std::cerr;
using std::endl;
using std::ifstream;
using std::list;
using std::vector;
using std::pair;
using std::make_pair;
using std::stable_sort;
using std::istringstream;
using std::ofstream;
using std::ceil;


std::list<subckt *> ckt::_subckt_list;

void ckt::free_subckt_list()
{
  list<subckt*>::iterator iter1;
  
  for(iter1 = _subckt_list.begin(); iter1 != _subckt_list.end(); ++iter1)
    delete *iter1;
}


subckt* ckt::get_subckt_by_name(string& name)
{
  list<subckt*>::iterator iter;

  for(iter = _subckt_list.begin(); iter != _subckt_list.end(); ++iter)
    {
      if((*iter)->get_name() == name)
	{
	  return *iter;
	}
    }

  return NULL;
}


ckt::~ckt()
{
  list<element *>::iterator iter;
  list<subckt_ins*>::iterator iter2;


  for(iter = _element_list.begin(); iter != _element_list.end(); ++iter)
    delete *iter;


  for(iter2 = _subckt_ins_list.begin(); iter2 != _subckt_ins_list.end(); ++iter2)
    delete *iter2;

  if(_partition_label != NULL)
    delete[] _partition_label;
}


void ckt::parse_line(string& line, string& oline)
{

  element *ptr;
  string mname;
  string dname;
  string sname;
  string gname;
  string bname;
  string pname;
  string nname;
  string svalue;
  string temp;
  string port;
  string special_node;
  istringstream iss;
  istringstream isso;
  list<string> port_list;
  list<string>::iterator iter;
  bool unit_status;
  double value;
  subckt_ins* ins_ptr;
  string org_cwd;
  string abs_dir;
  int idx;
  bool extra_property;

  
  if(line[0] == '*')
    {
      _reserved_header.push_back(line);
      if(_special_node_mode == false)
	{
	  if(line.find("special nodes") != string::npos)
	    {
	      _special_node_mode = true;
	    }
	  return;

	}
	  
      iss.clear();
      iss.str(line);

      iss >> special_node;

      if(iss >> special_node)
	_nl.nodename2num(special_node);
      else
	_special_node_mode = false;

      return;
    }

      
  if(_subckt_mode == false)
    {
      switch(line[0])
	{
	case 'c':
	  iss.clear();
	  iss.str(line);
	  iss >> temp >> pname >> nname >> svalue;

	  value = process_unit(svalue, unit_status);

	  extra_property = iss >> temp;
	  if(!unit_status || (extra_property && temp.find('$') == string::npos) )
	    {
	      _nl.nodename2num(pname);
	      _nl.nodename2num(nname);
	      _reserved_tail.push_back(oline);
	    }
	  else
	    {
	      // a parasitic capacitor
	      ptr = new cap(pname, nname, value);
	      _element_list.push_back(ptr);	
	    }
	      	      
	  break;
	  
	case 'r':
	  iss.clear();
	  iss.str(line);
	  iss >> temp >> pname >> nname >> svalue;

	  value = process_unit(svalue, unit_status);

	  extra_property = iss >> temp;
	  if(!unit_status || (extra_property && temp.find('$') == string::npos))
	    {
	      _nl.nodename2num(pname);
	      _nl.nodename2num(nname);
	      _reserved_tail.push_back(oline);
	    }
	  else
	    {
	      // a parasitic capacitor
	      ptr = new res(pname, nname, 1.0 / value);
	      _element_list.push_back(ptr);	
	    }
	  break;

	case 'j':
	case 'q':
	case 'm':
	  iss.clear();
	  iss.str(line);
	  iss >> mname >> dname >> gname >> sname >> bname;
	  _nl.nodename2num(dname);
	  _nl.nodename2num(gname);
	  _nl.nodename2num(sname);
	  _nl.nodename2num(bname);
	  _reserved_tail.push_back(oline);
	  break;

	case 'x':
	  ins_ptr = new subckt_ins(oline);
	  iss.clear();
	  iss.str(line);
	  iss >> temp; // name
	  ins_ptr->set_ins_name(temp);
	  while(iss >> port)
	    {
	      if(port.find('=') != string::npos)
		ins_ptr->add_prop(port);
	      else
		port_list.push_back(port);
	    }

	  ins_ptr->set_ref_name(port_list.back());
	  port_list.pop_back();


	  for(iter = port_list.begin(); iter != port_list.end(); ++iter)
	    ins_ptr->add_port(*iter);

	  _subckt_ins_list.push_back(ins_ptr);
	  break;

	case 'l':
	case 'd':
	case 'v':
	case 'i':
	  iss.clear();
	  iss.str(line);
	  iss >> temp >> port >> temp;
	  _nl.nodename2num(port);
	  _nl.nodename2num(temp);
	  _reserved_tail.push_back(oline);
	  break;

	case '.':
	  iss.clear();
	  iss.str(line);
	  iss >> temp;

	  if(temp == ".subckt")
	    {
	      _subckt_mode = true;
	      if(_current_sckt != NULL)
		{
		  _subckt_stack.push(_current_sckt);
		}
	      _current_sckt = new subckt;
	      iss >> temp;
	      _current_sckt->set_subckt_name(temp);
	      while(iss >> temp)
		{
		  if(temp.find('=') != string::npos)
		    {
		      _current_sckt->add_prop(temp);
		      _current_sckt->set_pure_para(false);
		    }
		  else
		    _current_sckt->add_port(temp);
		}
	    }
	  else if(temp == ".inc" || temp == ".include")
	    {
	      isso.clear();
	      isso.str(oline);
	      isso >> temp >> temp;
	      if(temp[0] == '\'' || temp[0] == '\"')
		{
		  temp = temp.substr(1, temp.size() - 2);
		      
		}
		  
	      org_cwd = _cwd;		  
	      idx = temp.rfind('/');
		  
	      if(temp[0] == '/')
		{
		  _cwd = temp.substr(0, idx+1);
		  abs_dir = temp;
		}
	      else
		{
		  abs_dir = _cwd + temp;
		  _cwd += temp.substr(0, idx+1);
		}
	      parse(abs_dir.c_str());
	      _cwd = org_cwd;		  
		  
	    }
	  else
	    {
	      _reserved_tail.push_back(oline);
	    }
	      
	  break;

	case 'w':
	case 'u':
	case 't':
	case 's':
	  cerr << "Error: Transmission line is not supported." << endl;
	  exit(-1);
	  break;

	case 'e':
	case 'f':
	case 'g':
	case 'h':
	  cout << "Warning: Controlled sources are not well supported now." << endl;
	  break;
	  
	default:
	  _reserved_tail.push_back(oline);
	  break;
	}
    }
  else
    {
      if(line[0] != '.')
	_current_sckt->parse_line(oline);
      else
	{
	  iss.clear();
	  iss.str(line);
	  iss >> temp;

	  if(temp == ".ends")
	    {
	      _subckt_list.push_back(_current_sckt);

	      if(!_subckt_stack.empty())
		{
		  _current_sckt = _subckt_stack.top();
		  _subckt_stack.pop();
		}
	      else
		{
		  _current_sckt = NULL;
		  _subckt_mode = false;
			      
		}
	    }
	  else if(temp == ".subckt")
	    {
	      _subckt_mode = true;
	      if(_current_sckt != NULL)
		{
		  _subckt_stack.push(_current_sckt);
		}
	      _current_sckt = new subckt;
	      iss >> temp;
	      _current_sckt->set_subckt_name(temp);
	      while(iss >> temp)
		{
		  if(temp.find('=') != string::npos)
		    {
		      _current_sckt->add_prop(temp);
		      _current_sckt->set_pure_para(false);
		    }
		  else
		    _current_sckt->add_port(temp);
		}
	    }
	  else if(temp == ".inc" || temp == ".include")
	    {
	      isso.clear();
	      isso.str(oline);
	      isso >> temp >> temp;
	      if(temp[0] == '\'' || temp[0] == '\"')
		{
		  temp = temp.substr(1, temp.size() - 2);
		      
		}
		  
	      org_cwd = _cwd;		  
	      idx = temp.rfind('/');
		  
	      if(temp[0] == '/')
		{
		  _cwd = temp.substr(0, idx+1);
		  abs_dir = temp;
		}
	      else
		{
		  abs_dir = _cwd + temp;
		  _cwd += temp.substr(0, idx+1);
		}
	      parse(abs_dir.c_str());
	      _cwd = org_cwd;
		  
	    }
	  else
	    {
	      _current_sckt->add_tail(oline);
	    }
	      
	}
	  
    }
}


void ckt::parse(const char* filename)
{

  ifstream inf(filename);

  if(!inf)
    {
      cout << "File " << filename << " Read Error!" << endl;
      cout << "Exit!" << endl;
      exit(-1);
    }

  string line;
  string oline;
  string combined_lines;
  string line_temp;
  unsigned int i, s_beg, s_end;
  string trans_combined_lines;

  
  std::istringstream issm;

  _nl.nodename2num("0");
  while(!inf.eof())
    {
      getline(inf, line_temp);

      for(i = 0; i < line_temp.size(); ++i)
	if(line_temp[i] != ' ' && line_temp[i] != '\t')
	  break;

      s_beg = i;

      for(i = s_beg; i < line_temp.size(); ++i)
	if(line_temp[i] == '$')
	  break;

      s_end = i;

      line_temp = line_temp.substr(s_beg, s_end-s_beg);

      if(line_temp == "")
	continue;

      if(line_temp[0] != '+')
	{
	  oline = combined_lines;
	  combined_lines = line_temp;
	}
      else
	{
	  combined_lines += " ";
	  combined_lines += line_temp.substr(1, line_temp.size());
	  oline = "";
	}

      if(oline == "")
	continue;
      
      line = oline;
      transform(oline.begin(), oline.end(), line.begin(), tolower);

      parse_line(line, oline);

    }

  trans_combined_lines = combined_lines;
  transform(combined_lines.begin(), combined_lines.end(), trans_combined_lines.begin(), tolower);
  parse_line(trans_combined_lines, combined_lines);

  inf.close();

  
}


int ckt::expand()
{
  int expanded_no = 0;
  subckt* psckt;
  list<subckt_ins*>::iterator iter;
  list<element*>::iterator e_iter;
  list<element*> element_list;
  int index;
  string port;
  string hier_name;
  string pos, neg;
  element * ptr;

  for(iter = _subckt_ins_list.begin(); iter != _subckt_ins_list.end();)
    {
      if((*iter)->get_num_props() > 0)
	{
	  ++iter;
	  continue;
	}
      
      psckt = get_subckt_by_name((*iter)->get_ref_name());
      if(psckt == NULL)
	{
	  cout << "subckt " << (*iter)->get_ref_name().c_str() << " not defined!" << endl;
	  exit(-1);
	}

      // this subckt can be expanded
      if(psckt->is_pure_para() && (!psckt->get_subckt_ins_num()))
	{
	  ++expanded_no;
	  element_list = psckt->get_element_list();
	  for(e_iter = element_list.begin(); e_iter != element_list.end(); ++e_iter)
	    {
	      port = (*e_iter)->get_pos_port();
	      index = psckt->find_port(port);
	      if(index == -2) // not a port
		{
		  hier_name = (*iter)->get_ins_name() + ".";
		  hier_name += port;
		}
	      else if(index == -1) // ground port
		{
		  hier_name = "0";
		}
	      else // port
		{
		  hier_name = (*iter)->get_port(index);
		}

	      pos = hier_name;
	      
	      port = (*e_iter)->get_neg_port();
	      index = psckt->find_port(port);	      
	      if(index == -2) // not a port
		{
		  hier_name = (*iter)->get_ins_name() + ".";
		  hier_name += port;
		}
	      else if(index == -1) // ground
		{
		  hier_name = "0";
		}
	      else
		{
		  hier_name = (*iter)->get_port(index);
		}

	      neg = hier_name;

	      if((*e_iter)->get_type() == 'c')
		ptr = new cap(pos, neg, (*e_iter)->get_value());
	      else
		ptr = new res(pos, neg, (*e_iter)->get_value());
	      
	      _element_list.push_back(ptr);
	      
	    } // end internal for

	  // remove this subckt instance
	  delete *iter;
	  iter = _subckt_ins_list.erase(iter);
	} // end if
      else
	{
	  ++iter;
	}
    } //end external for

  return expanded_no;
}


void ckt::post_parse()
{
  int expand_times = 0;
  int expand_no = 0;
  list<subckt* >::iterator s_iter;
  list<subckt_ins*>::iterator si_iter;

  
  while(1)
    {
      expand_no = 0;
      ++expand_times;
      expand_no += expand();
      for(s_iter = _subckt_list.begin(); s_iter != _subckt_list.end(); ++s_iter)
	{
	  if((*s_iter)->get_num_subckt_ins() != 0)
	    expand_no += (*s_iter)->expand();
	}

      if(expand_no == 0 || expand_times > 20)
	break;
    }


  // post processing the remaining subckt instances
  for(si_iter = _subckt_ins_list.begin(); si_iter != _subckt_ins_list.end(); ++si_iter)
    {
      vector<string>& port_vec = (*si_iter)->get_port_vec();
      vector<string>::iterator str_iter;
      for(str_iter = port_vec.begin(); str_iter != port_vec.end(); ++str_iter)
	{
	  _nl.nodename2num(*str_iter);
	}
      _reserved_header.push_back((*si_iter)->get_line());
      _referenced_subckts[(*si_iter)->get_ref_name()] = 1;
    }

  
  // check the unreferenced subckts, and remove these subckts from the subckt list
  for(s_iter = _subckt_list.begin(); s_iter != _subckt_list.end(); ++s_iter)
    {
      (*s_iter)->collect_referenced_subckts(_referenced_subckts);
    }


  // post parse
  int i;
  _num_ports = _nl.node_nums();

  list<element *>::iterator iter;
  for(iter = _element_list.begin(); iter != _element_list.end(); ++iter)
    {
      (*iter)->load(_g_list, _c_list, _graph, this);
    }

  _num_nodes = _nl.node_nums();

  for(i = _num_ports+1; i <= _num_nodes; ++i)
    _g_list.stamp(i,i);
  

  if(_num_nodes < 1)
    {
      cout << "Warning: this circuit is not suitable for model order reduction! " << endl;
      cout << "Exit!" << endl;
      exit(-1);
    }  
}


void ckt::partition()
{
  int* block_label = new int[_num_nodes];
  int num_blocks;
  int i;
  int j;
  vector<int> sub_block_ind;
  vector<int>::iterator iter;

  _partition_label = new int[_num_nodes];

  num_blocks = _graph.connectedComponents(block_label);
  _block_id = _num_ports;

  for(i = 0; i < num_blocks; ++i)
    {
      sub_block_ind.clear();
      for(j = _num_ports; j < _num_nodes; ++j)
	{
	  if(block_label[j] == i)
	    sub_block_ind.push_back(j);
	}
      if(sub_block_ind.size() <= 2)
	{
	  for(iter = sub_block_ind.begin(); iter != sub_block_ind.end(); ++iter)
	    _partition_label[*iter] = _block_id++;
	}
	
      if(sub_block_ind.size() > 2)
	subblock_partition(sub_block_ind);      
    }

  // post-process the partition
  for(i = 0; i < _num_ports; ++i)
    _partition_label[i] = i;


//  #ifndef NDEBUG
ofstream outf("partition");

for(i = 0; i < _num_nodes; ++i)
{
    outf << i << " " << _nl.num2nodename(i+1)  << " "  << _partition_label[i] << endl;
}
  
//dump_graph(_g_list.get_data(), _num_ports, _partition_label, _num_nodes, num_blocks, block_label);
//  #endif
  
  delete[] block_label;

}



void ckt::reduction()
{
  int i;
  map<int, double>& g_diags = _g_list.get_diags();
  map<int, double>& c_diags = _c_list.get_diags();
  map<int, map<int, double> > & g_data = _g_list.get_data();
  map<int, map<int, double> > & c_data = _c_list.get_data();
  map<int, map<int, double> > & red_g_data = _red_g_list.get_data();
  map<int, map<int, double> > & red_c_data = _red_c_list.get_data();

  map<int, double>::iterator iter;

  for(i = 0; i < _num_nodes; ++i)
    {
      red_g_data[_partition_label[i]][_partition_label[i]] += g_diags[i];
      red_c_data[_partition_label[i]][_partition_label[i]] += c_diags[i];
    }

  for(i = 0; i < _num_nodes; ++i)
    {
      for(iter = g_data[i].begin(); iter != g_data[i].end(); ++iter)
	{
	  if(iter->first > i && _partition_label[i] != _partition_label[iter->first])
	    {
	      red_g_data[_partition_label[i]][_partition_label[iter->first]] += iter->second;
	      red_g_data[_partition_label[iter->first]][_partition_label[i]] += iter->second;
	    }
	}
    }

   for(i = 0; i < _num_nodes; ++i)
    {
      for(iter = c_data[i].begin(); iter != c_data[i].end(); ++iter)
	{
	  if(iter->first > i && _partition_label[i] != _partition_label[iter->first])
	    {
	      red_c_data[_partition_label[i]][_partition_label[iter->first]] += iter->second;
	      red_c_data[_partition_label[iter->first]][_partition_label[i]] += iter->second;
	    }
	}
    }

}

void ckt::dump_netlist(const char* outfile)
{
  int device_id = 0;
  int i;
  ofstream outf(outfile);

  #ifndef TIME_NDEBUG
  timer ti;
  int subckt_index = 0;
  ti.start();
  #endif

  if(!outf)
    {
      cout << "File " << outfile << " Write Error!" << endl;
      cout << "Exit!" << endl;
      exit(-1);
    }

  outf << "* Reduced Circuit Generated by Model Order Reduction Tool" << endl;

  list<string>::iterator iter_l;
  for(iter_l = _reserved_header.begin(); iter_l != _reserved_header.end(); ++iter_l)
    {
      //  outf << iter_l->c_str() << endl;
      dump_line(*iter_l, outf);
    }

  map<int, map<int, double> >& red_g_data = _red_g_list.get_data();
  map<int, map<int, double> >& red_c_data = _red_c_list.get_data();
  map<int, double>::iterator iter;
  string node_name;

  for(i = 0; i < _num_nodes; ++i)
    {
      for(iter = red_g_data[i].begin(); iter != red_g_data[i].end(); ++iter)
	{
	  if(iter->first > i)
	    {
	      outf << "Rred_" << device_id++ << " ";
	      if(i < _num_ports)
		{
		  outf << _nl.num2nodename(i+1).c_str();
		}
	      else
		{
		  outf << "inode" << i;
		}

	      outf << " ";

	      if(iter->first < _num_ports)
		{
		  outf << _nl.num2nodename(iter->first + 1).c_str();
		}
	      else
		{
		  outf << "inode" << iter->first;
		}

	      outf << " " << -1/(iter->second);
	      outf << endl;
	    }
	}
    }

    for(i = 0; i < _num_nodes; ++i)
    {
      for(iter = red_c_data[i].begin(); iter != red_c_data[i].end(); ++iter)
	{
	  if(iter->first > i && -iter->second > _ceps)
	    {
	      outf << "Cred_" << device_id++ << " ";
	      if(i < _num_ports)
		{
		  outf << _nl.num2nodename(i+1).c_str();
		}
	      else
		{
		  outf << "inode" << i;
		}

	      outf << " ";

	      if(iter->first < _num_ports)
		{
		  outf << _nl.num2nodename(iter->first + 1).c_str();
		}
	      else
		{
		  outf << "inode" << iter->first;
		}

	      outf << " " << -(iter->second);
	      outf << endl;
	    }
	}
    }

    for(i = 0; i < _num_nodes; ++i)
      {
	if(fabs(red_g_data[i][i]) > _geps)
	  {	
	    outf << "Rred_" << device_id++ << " ";
	    if(i < _num_ports)
	      outf << _nl.num2nodename(i+1).c_str();
	    else
	      outf << "inode" << i;

	    outf << " 0 ";
	    outf << 1/red_g_data[i][i];
	    outf << endl;
	  }


       	if(fabs(red_c_data[i][i]) > _ceps)
	  {
	    outf << "Cred_" << device_id++ << " ";
	    if(i < _num_ports)
	      outf << _nl.num2nodename(i+1).c_str();
	    else
	      outf << "inode" << i;

	    outf << " 0 ";
	    outf << red_c_data[i][i];
	    outf << endl;
	  }
      }

    #ifndef TIME_NDEBUG
    cout << "main ckt dump time: " << ti.end() << endl;
    #endif

    // subckt partition
    list<subckt*>::iterator iter1;
    for(iter1 = _subckt_list.begin(); iter1 != _subckt_list.end(); ++iter1)
      {
	// skip the unreferenced subckts
	if(_referenced_subckts.find((*iter1)->get_name()) == _referenced_subckts.end())
	{
	  continue;
	}

	
	(*iter1)->set_max_blocksize(_subblock_threshold);

	#ifndef TIME_NDEBUG
	ti.start();
	#endif

	(*iter1)->post_parse();

	#ifndef TIME_NDEBUG
	cout << "subckt #" << subckt_index << " parse time: " << ti.end() << endl;
	ti.start();
        #endif
	
	(*iter1)->partition();

	#ifndef TIME_NDEBUG
	cout << "subckt #" << subckt_index << " partition time: " << ti.end() << endl;
	ti.start();
        #endif
	
	(*iter1)->reduction();

	#ifndef TIME_NDEBUG
	cout << "subckt #" << subckt_index << " reduction time: " << ti.end() << endl;
	ti.start();
        #endif
	
	(*iter1)->dump_netlist(outf);

	#ifndef TIME_NDEBUG
	cout << "subckt #" << subckt_index << " dump time: " << ti.end() << endl;
        ++subckt_index;
        #endif
      }
  

  for(iter_l = _reserved_tail.begin(); iter_l != _reserved_tail.end(); ++iter_l)
    {
      // outf << iter_l->c_str() << endl;
      dump_line(*iter_l, outf);
    }

}


void ckt::subblock_partition(vector<int>& sub_block_ind)
{
  eigs_wrapper eigs_solver;
  vector<int> inds;
  int size = sub_block_ind.size();
  int pnums = ceil((double) size / (double)_subblock_threshold);
  int i,j;

  double* eigvals = NULL;
  double* eigvecs = NULL;
  
  int numvec = 2;
  int ret=1;

  while(ret && numvec < 100)
    {
      if(eigvecs != NULL)
	delete[] eigvecs;
      eigvecs = new double[numvec * size];

      if(eigvals != NULL)
	delete[] eigvals;
      eigvals = new double[numvec];

      ret = eigs_solver.eigs(_g_list, sub_block_ind, numvec, eigvals, eigvecs);
      if(ret != 0)
	numvec *= 2;
    }

  if(ret != 0)
    {
      cerr << "EIGS failure!" << endl;
      cerr << "Exit!" << endl;
      exit(-1);
    }

  #ifndef NDEBUG
  static bool flag = true;
  #endif

  int* ind = new int[size];
  double* sorted_values = new double[size];

  #ifndef NDEBUG
  if(flag)
    {
      cout << "before sorting" << endl;
      for(i = 0; i < size; ++i)
	{
	  cout << i << ": " << eigvecs[size + i] << endl;
	}
    }
  #endif

  asort(ind, sorted_values, size, &eigvecs[size]);

  #ifndef NDEBUG
  if(flag)
    {
      cout << "after sorting: " << endl;
      for(i = 0; i < size; ++i)
	{
	  cout << ind[i] << ": " << sorted_values[i] << endl;
	}
    }
  #endif
  
  diff(size, sorted_values);

  #ifndef NDEBUG
  if(flag)
    {
      cout << "difference: " << endl;
      for(i = 0; i < size; ++i)
	{
	  cout << i << ": " << sorted_values[i] << endl;
	}
    }
  #endif

  int* ind1 = new int[size-1];
  dsort(ind1, sorted_values, size-1, sorted_values);

  // for(i = 0; i < size - 1; ++i)
  //  {
 //     if(sorted_values[i] < _relative_tol * sorted_values[0])
 // 	break;
 //   }

 // if(pnums > i + 1)
 //   pnums = i + 1;

  //  if(pnums > 1)

/*
  for(i = pnums-1; i < size-1; ++i)
    {
      if(sorted_values[i] * eigvals[1] < _relative_tol)
	break;
    }

  if(i > pnums - 1)
    pnums = i + 1;
*/

//  cout << "gap: " << sorted_values[pnums] * eigvals[1] << " pnums: " << pnums << "size: " << size << " ";
//   cout << "sorted_values: " << sorted_values[pnums] << "eigvals: " << eigvals[1] << endl;

  #ifndef NDEBUG
  if(flag)
    {
      cout << "difference sorting " << endl;
      for(i = 0; i < size-1; ++i)
	{
	  cout << ind1[i] << ": "  << sorted_values[i] << endl;
	}
    }
  #endif
  
  stable_sort(ind1, ind1 + pnums - 1);

  int* conn_label = new int[_subblock_threshold];
  int* final_ind = new int[pnums + 1];
  final_ind[0] = 0;
  final_ind[pnums] = size;
  int num_check;

  #ifndef NDEBUG
  flag = false;
  #endif

  for(i = 0; i < pnums-1; ++i)
    {
      final_ind[i+1] = ind1[i] + 1;
    }

  for(i = 0; i < pnums; ++i)
    {
      // label small blocks
      if(final_ind[i+1] - final_ind[i] <= _subblock_threshold)
	{

	  check_conn(sub_block_ind, ind, final_ind, i, conn_label, num_check);
	  
	  for(j = final_ind[i]; j < final_ind[i+1]; ++j)
	    _partition_label[sub_block_ind[ind[j]]] = _block_id + conn_label[j-final_ind[i]];
	  
	  _block_id = _block_id + num_check;
	}
      else
	{
	  inds.clear();
	  for(j = final_ind[i]; j < final_ind[i+1]; ++j)
	    inds.push_back(sub_block_ind[ind[j]]);
	  
	  stable_sort(inds.begin(), inds.end());
	  
	  subblock_partition(inds);
	}
      
    }
  

  delete[] ind;
  delete[] ind1;
  delete[] final_ind;
  delete[] sorted_values;
  delete[] eigvals;
  delete[] eigvecs;
  delete[] conn_label;
}


void ckt::check_conn(vector<int>& sub_block_ind, int* ind, int* final_ind, int k, int* conn_label, int& num_check)
{
  map<int, map<int, double> >& g = _g_list.get_data();
  Graph g_graph;
  map<int, double>::iterator iter;

  for(int i=final_ind[k]; i < final_ind[k+1]; ++i)
    {

      for(iter = g[sub_block_ind[ind[i]]].begin(); iter != g[sub_block_ind[ind[i]]].end(); iter++)
	{
	  for(int j=final_ind[k]; j < final_ind[k+1]; ++j)
	    {
	      if(iter->first == sub_block_ind[ind[j]])
		{
			g_graph.addEdge(i-final_ind[k], j-final_ind[k]);
		}
	    }
	}

    }

  num_check = g_graph.connectedComponents(conn_label);

}


void ckt::diff(int size, double* values)
{
  int i;
  for(i = 0; i < size -1; ++i)
    {
      values[i] = values[i+1] - values[i];
    }
}

void ckt::asort(int* ind, double* sorted_values, int size, double* values)
{
  vector<pair<int, double> > data;
  int i;

  for(i = 0; i < size; ++i)
    {
      data.push_back(make_pair(i, values[i]));
    }

  stable_sort(data.begin(), data.end(), sort_less());

  for(i = 0; i < size; ++i)
    {
      ind[i] = data[i].first;
      sorted_values[i] = data[i].second;
    }

  
}

void ckt::dsort(int* ind, double* sorted_values, int size, double* values)
{
  vector<pair<int, double> > data;
  int i;

  for(i = 0; i < size; ++i)
    {
      data.push_back(make_pair(i, values[i]));
    }

  stable_sort(data.begin(), data.end(), sort_great());

  for(i = 0; i < size; ++i)
    {
      ind[i] = data[i].first;
      sorted_values[i] = data[i].second;
    }
}


void ckt::dump_line(std::string& line, ofstream & outf)
{
  istringstream iss(line);
  string temp;
  int j = 0;

  //skip the comments
  if(line[0] == '*')
    {
      //      outf << line.c_str() << endl;
      return;
    }

  while(iss >> temp)
    {
      outf << temp.c_str() << " ";
      ++j;
      if(j % 20 == 0)
	{
	  if(temp == "=")
	    {
	      iss >> temp;
	      outf << temp.c_str() << " ";
	    }
	  outf << endl;
          if(iss >> temp)
            {
	      outf << "+ " << temp.c_str() << " ";
               ++j;
            }
	}
    }

  outf << endl;
  
}
