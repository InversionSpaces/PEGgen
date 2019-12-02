#pragma once

#include <vector>
#include <string>
#include <fstream>
#include <cassert>

using namespace std;

struct Node {
	string data;
	
	vector<Node*> childs;
};

inline void purge_tree(const Node* root)
{
	assert(root);
	
	for (const auto& c: root->childs)
		purge_tree(c);

	delete root;
}

inline void dump_inner(const Node* root, ofstream& out)
{
	out << "NODE" << root 
		<< "[shape=box label=\"" << root->data
		<< "\"]\n";
	
	for (const auto& c: root->childs) {
		out << "NODE" << root 
			<< "-> NODE" << c << "\n";
		
		dump_inner(c, out);
	}
}

inline void dump_tree(const Node* root, ofstream& out)
{
	out << "digraph Tree {\n";
	dump_inner(root, out);
	out << "}\n";
}
