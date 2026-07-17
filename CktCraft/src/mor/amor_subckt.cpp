#include "amor_comm.h"
#include "amor_subckt.h"
#include "amor_element.h"
#include "amor_cap.h"
#include "amor_res.h"
#include "amor_eigs.h"
#include "amor_subckt_ins.h"
#include "amor_dump_dot.h"
#include "amor_unit.h"
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




int subckt::find_port(string name)
{
  if(_nl.is_exist(name))
    {
      return _nl.nodename2num(name) - 1;
    }
  else
    return -2;
}

void subckt::collect_referenced_subckts(map<string, int> & referenced_subckts)
{
   std::list<subckt_ins*>::iterator iter;
   
   for(iter = _subckt_ins_list.begin(); iter != _subckt_ins_list.end(); ++iter)
     referenced_subckts[(*iter)->get_ref_name()] = 1;
}


void subckt::parse_line(string& oline)
{
  string line;
  element *ptr;
  string mname;
  string dname;
  string sname;
  string gname;
  string bname;
  string port;
  string temp;
  istringstream iss;
  subckt_ins* ins_ptr;
  string pname;
  string nname;
  string svalue;
  double value;
  bool unit_status;
  bool extra_property;

  line = oline;
  transform(oline.begin(), oline.end(), line.begin(), tolower);

  list<string> port_list;
  list<string>::iterator iter;
  
  
  if(line == "")
    return;
      
  if(line[0] == '*')
    {
      _reserved_header.push_back(line);

    }

  iss.str(line);
  switch(line[0])
    {
    case 'c':
      iss >> temp >> pname >> nname >> svalue;
      
      value = process_unit(svalue, unit_status);

      extra_property = iss >> temp;
      if(!unit_status || (extra_property && temp.find('$') == string::npos))
	{
	  _nl.nodename2num(pname);
	  _nl.nodename2num(nname);
	  _reserved_tail.push_back(oline);
	  _pure_para = false;
	}
      else
	{
	  // a parasitic capacitor
	  ptr = new cap(pname, nname, value);
	  _element_list.push_back(ptr);	
	}	      
      break;
      
    case 'r':
      iss >> temp >> pname >> nname >> svalue;
      
      value = process_unit(svalue, unit_status);

      extra_property = iss >> temp;
      if(!unit_status || (extra_property && temp.find('$') == string::npos ))
	{
	  _nl.nodename2num(pname);
	  _nl.nodename2num(nname);
	  _reserved_tail.push_back(oline);
	  _pure_para = false;
	}
      else
	{
	  // a parasitic capacitor
	  ptr = new res(pname, nname, 1.0 / value);
	  _element_list.push_back(ptr);	
	}
      break;

    case 'q':
    case 'j':
    case 'm':
      _pure_para = false;
      iss >> mname >> dname >> gname >> sname >> bname;
      _nl.nodename2num(dname);
      _nl.nodename2num(gname);
      _nl.nodename2num(sname);
      _nl.nodename2num(bname);
      _reserved_tail.push_back(oline);
      break;

    case 'x':
      ins_ptr = new subckt_ins(oline);
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
      _pure_para = false;
      iss >> temp >> port >> temp;
      _nl.nodename2num(port);
      _nl.nodename2num(temp);
      _reserved_tail.push_back(oline);
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
      _pure_para = false;
      cout << "Warning: Controlled sources are not well supported now." << endl;
      break;
	  
    default:
      _reserved_tail.push_back(oline);
      break;
    }   
}


void subckt::post_parse()
{
  
  int i;
  list<subckt_ins*>::iterator si_iter;
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
    }
  
  _num_ports = _nl.node_nums();

  list<element *>::iterator iter;
  for(iter = _element_list.begin(); iter != _element_list.end(); ++iter)
    {
      (*iter)->load(_g_list, _c_list, _graph, this);
    }

  _num_nodes = _nl.node_nums();

  for(i = _num_ports+1; i <= _num_nodes; ++i)
    _g_list.stamp(i,i);

}



void subckt::dump_netlist(ofstream& outf)
{
  int device_id = 0;
  int i;
  int j;

  list<string>::iterator iter_l;
  vector<string>::iterator iter_v;

  outf << ".subckt " << _subckt_name.c_str() << " ";

  for(iter_l = _port_list.begin(), j = 0; iter_l != _port_list.end(); ++iter_l, ++j)
    {
      outf << iter_l->c_str() << " ";
      if(j % 20 == 0)
	outf << endl << "+ ";
    }
  
  for(iter_v = _prop_vec.begin(), j = 0; iter_v != _prop_vec.end(); ++iter_v, ++j)
    {
      outf << " " << iter_v->c_str() << " ";
      if(j % 20 == 0)
	outf << endl << "+ ";
    }
  

  outf << endl;
  
  for(iter_l = _reserved_header.begin(); iter_l != _reserved_header.end(); ++iter_l)
    {
      //      outf << iter_l->c_str() << endl;
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
  

  for(iter_l = _reserved_tail.begin(); iter_l != _reserved_tail.end(); ++iter_l)
    {
      //      outf << iter_l->c_str() << endl;
      dump_line(*iter_l, outf);
    }

  outf << ".ends" << endl;

}

