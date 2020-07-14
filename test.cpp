#include <iostream>
#include <string>

#include "header.hpp"

using namespace std;

int main() {
    string res;
    for (   string tmp; 
        getline(cin, tmp);
        res += tmp  );

    peg::Parser par(res.c_str());
    auto ast = par.parse();
    
    if (!ast.empty())
        ast.dump(cout);
}
