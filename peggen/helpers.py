ENDLESS_LOOP_HEADER = '''
while (1) {
'''

ENDLESS_LOOP_FOOTER = '''
}
'''

TMP_EXPECT = '''
tmp = expect({}, {});
'''

TMP_PARSE = '''
tmp = parse{}();
'''

TMP_POP = '''
tmp = pop();
'''

TMP_PUSH_BACK = '''
(*top())->childs.push_back(*tmp);
'''

__ESCAPE = '''
if (!{}) {{
        purge_tree(*top());
        top() = nullopt;

        reset();
        break;
}}
'''

TMP_ESCAPE = __ESCAPE.format("tmp")
CTMP_ESCAPE = __ESCAPE.format("ctmp")

CREATE_CHILD = '''
(*top())->childs.push_back(
        new Node {string(1, *ctmp)}
);
'''

CREATE_IF_CTMP = f'''
if (ctmp) {{
    {CREATE_CHILD}
}}
'''

ADD_CHAR = '''
(*top())->childs.back()->data += *ctmp;
'''

CTMP_SYMBOL = '''
ctmp = symbol({});
'''

ADD_WHILE_CTMP = f'''
while (ctmp) {{{{
        {CTMP_SYMBOL}

        if (ctmp) {{{{
                {ADD_CHAR}
        }}}}
        else break;
}}}}
'''

INSERT_CHILDS = '''
(*top())->childs.insert(
    (*top())->childs.end(),
    (*tmp)->childs.begin(),
    (*tmp)->childs.end()
);
delete *tmp;
'''

INSERT_IF_TMP = f'''
if (tmp) {{
    {INSERT_CHILDS}
}}
'''

INSERT_IF_TMP_ELSE_BREAK = INSERT_IF_TMP + '''
else break;
'''

PARSE_METHOD = '''
optional<Node*> parse() {{
        return parse{}();
}}
'''

TOP_NEW_NODE = '''
    top() = new Node{};
'''

WILDCARD_HEADER = '''
// WILDCARD {} : {}
'''

WILDCARD_FOOTER = '''
// END WILDCARD {} : {}
'''

ALT_HEADER = '''
// ALT {}
while (!top()) {{
        mark();
'''

ALT_FOOTER = '''
        unmark();
}}
// END ALT {}
'''

ALTS_HEADER = '''
// ALTS {}
push(nullopt);
'''

ALTS_FOOTER = '''
// END ALTS {}
assert(results.size() == init_size + {});
'''

RULE_HEADER = '''
optional<Node*> parse{}() {{
        const size_t init_size = results.size();

        optional<Node*> tmp = nullopt;
        optional<char> ctmp = nullopt;
'''

RULE_FOOTER = '''
        tmp = pop();
        if (tmp) {{
                (*tmp)->data = "{}";
        }}

        return tmp;
}}
'''

CLASS_HEADER = '''
#include <cstring>
#include <string>
#include <iostream>
#include <stack>
#include <optional>
#include <cassert>
#include <cstdlib>

#include "Node.hpp"

using namespace std;

class Parser
{
private:
        const char* input;
        stack<const char*> marks;
        stack<optional<Node*> > results;
public:
        Parser(const char* input) : input(input)
        {
        }

        inline void skip()
        {
                while (*input && isspace(*input)) input++;
        }

        inline optional<char> symbol(const char* c)
        {
                skip();
                if (*input && strchr(c, *input) != NULL) {
                        char retval = *input;
                        input++;
                        return retval;
                }
                return nullopt;
        }

        inline void mark()
        {
                marks.push(input);
        }

        inline void unmark()
        {
                marks.pop();
        }

        inline void reset()
        {
                input = marks.top();
                marks.pop();
        }

        inline optional<Node*> pop()
        {
                auto retval = results.top();
                results.pop();
                return retval;
        }

        inline void push(optional<Node*> res)
        {
                results.push(res);
        }

        inline void drop()
        {
                optional<Node*> temp = results.top();
                results.pop();
                results.top() = temp;
        }

        inline optional<Node*>& top()
        {
                return results.top();
        }

        const char* pos()
        {
                return input;
        }

        optional<Node*> expect(const char* s, int n)
        {
                skip();
                if (strncmp(input, s, n) == 0) {
                        input += n;
                        return new Node {s};
                }
                return nullopt;
        }
'''

CLASS_FOOTER = '''
};
'''
