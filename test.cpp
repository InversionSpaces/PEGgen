#include <iostream>
#include <string>

#include "header.hpp"

using namespace std;

int main() {
	string res;
	for (	string tmp; 
		getline(cin, tmp);
		res += tmp 	);

	Parser par(res.c_str());
	auto ast = par.parse();
	
	if (ast) {
		dump_tree(*ast, cout);
		purge_tree(*ast);
	}
	else
		cout << "Error parsing";
}
