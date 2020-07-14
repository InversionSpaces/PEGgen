#pragma once

#include <vector>
#include <string>
#include <fstream>
#include <cassert>
#include <iostream>

namespace peg {
class AbstractTree {
public:
    struct Node {
        std::string data;
        std::vector<Node*> childs;
    };

    AbstractTree(Node* root) : root(root) {}

    AbstractTree(const AbstractTree& other) = delete;
    AbstractTree(AbstractTree&& other) = delete;

    static inline void purge(const Node* root)
    {
        assert(root);

        for (const auto& c: root->childs)
            purge(c);

        delete root;
    }

    inline void dump(std::ostream& out) const
    {
        out << "digraph Tree {\n";
        dump_inner(root, out);
        out << "}\n";
    }

    inline bool empty() const {
        return root == nullptr;
    }

    ~AbstractTree() {
        if (root) purge(root);
    }
private:
    Node* root;

    static inline void dump_inner(const Node* root, std::ostream& out)
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
};
}
