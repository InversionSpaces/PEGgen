from tokenize import tokenize, NAME, STRING, NEWLINE
from pprint import pprint
from io import BytesIO
from collections import namedtuple

Token = namedtuple("Token", ["type", "str"])

class Tokenizer:
	def __init__(self, fp):
		self.__tokenizer = tokenize(fp.readline)
		self.__tokens = list()
		self.__pos = 0;
		
		try:
			next(self.__tokenizer) # To skip encoding
		except StopIteration:
			pass
	
	def get_pos(self):
		return self.__pos
		
	def set_pos(self, pos):
		self.__pos = pos
		
	def get_token(self):
		token = self.peek_token()
		if (token): self.__pos += 1
		return token
		
	def peek_token(self):
		if self.__pos < len(self.__tokens):
			return self.__tokens[self.__pos]
			
		try:
			token = Token(*next(self.__tokenizer)[:2])
			self.__tokens.append(token)
			return token
		except StopIteration	:
			return None

class Parser:
	def __init__(self, fp):
		self.__tokenizer = Tokenizer(fp)
		
	def get(self):
		return self.__tokenizer.get_pos()
	
	def set(self, pos):
		self.__tokenizer.set_pos(pos)
	
	def expect(self, arg):
		token = self.__tokenizer.peek_token()
		if token.str == arg or token.type == arg:
			return self.__tokenizer.get_token()
		return None;

Rule = namedtuple("Rule", ["name", "alts"])

Wildcard = namedtuple("Wildcard", ["op", "alts"])
Charset = namedtuple("Charset", ["op", "chars"])

class GrammarParser(Parser):
	
	def parseCharset(self):
		pos = self.get()
		
		if not self.expect("["):
			self.set(pos)
			return None
		
		chars = self.expect(STRING)
		if not chars:
			self.set(pos)
			return None
		
		if not self.expect("]"):
			self.set(pos)
			return None
		
		if self.expect("+"):
			return Charset("+", chars.str)
		
		if self.expect("*"):
			return Charset("*", chars.str)
		
		if self.expect("?"):
			return Charset("?", chars.str)
			
		return Charset("", chars.str)
			
	def parseWildcard(self):
		pos = self.get()
		
		if not self.expect("("):
			self.set(pos)
			return None
		
		alts = self.parseAlternatives()
		if not alts:
			self.set(pos)
			return None
		
		if not self.expect(")"):
			self.set(pos)
			return None
		
		if self.expect("+"):
			return Wildcard("+", alts)
		
		if self.expect("*"):
			return Wildcard("*", alts)
		
		if self.expect("?"):
			return Wildcard("?", alts)
			
		return Wildcard("", alts)
		
	def parseAlternatives(self):		
		alt = self.parseAlternative()
		if not alt:
			return None
			
		alts = [alt]
		while True:
			if not self.expect("|"):
				return alts
			
			alt = self.parseAlternative()
			
			if not alt:
				return alts
			
			alts.append(alt)
	
	def parseAlternative(self):
		token = (	self.expect(NAME) or 
					self.expect(STRING)	or
					self.parseCharset() or
					self.parseWildcard()	)
					
		if not token:
			return None
		
		alt = [token]
		while True:
			token = (	self.expect(NAME) or 
						self.expect(STRING)	or
						self.parseCharset() or
						self.parseWildcard()	)
			
			if not token:
				return alt
			
			alt.append(token)
	
	def parseRule(self):
		pos = self.get()
		
		name = self.expect(NAME)
		if not name:
			self.set(pos)
			return None
		
		if not self.expect("->"):
			self.set(pos)
			return None
		
		alts = self.parseAlternatives()
		if not alts:
			self.set(pos)
			return None
			
		if not self.expect(NEWLINE):
			self.set(pos)
			return None
		
		return Rule(name.str, alts)
		
	def parseGrammar(self):
		rule = self.parseRule()
		retval = list()
		
		while rule:
			retval.append(rule)
			rule = self.parseRule()
		
		return retval
		
class PEGGenerator:
	def __init__(self, grammar, fp):
		self.__grammar = grammar
		self.__fp = fp
		self.depth = 0
	
	class_header = '''
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
		
		inline optional<char> symbol(const char* c, size_t n)
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
	
	escape = '''
		if (!tmp) {
			purge_tree(*top());
			top() = nullopt;
			
			reset();
			break;
		}
	'''
	
	cescape = '''
		if (!ctmp) {
			purge_tree(*top());
			top() = nullopt;
			
			reset();
			break;
		}
	'''
	
	mkstr = '''
		(*top())->childs.push_back(
			new Node {string(1, *ctmp)}
		);
	'''
	
	addchr = '''
		(*top())->childs.back()->data += *ctmp;
	'''
	
	insert = '''
		(*top())->childs.insert((*top())->childs.end(),
		(*tmp)->childs.begin(), (*tmp)->childs.end());
		delete *tmp;
	'''
	
	def part(self, part):
		if isinstance(part, Token):
			if part.type == STRING:
				self.__fp.write(f'''
					tmp = expect({part.str}, {len(part.str) - 2});
				''')
				
			elif part.type == NAME:
				self.__fp.write(f'''
					tmp = parse{part.str}();
				''')
				
			self.__fp.write(self.escape)
			
			self.__fp.write('''
				(*top())->childs.push_back(*tmp);
			''')
				
		if isinstance(part, Wildcard):
			self.__fp.write(f'''
				// WILDCARD {part.op} : {part.alts}
			''')
				
			if part.op == "":
				self.alts(part.alts)
				self.__fp.write('''
					tmp = pop();
				''')
				self.__fp.write(self.escape)
				self.__fp.write(self.insert);
				
			elif part.op == "+":
				self.alts(part.alts)
				self.__fp.write('''
					tmp = pop();
				''')
				self.__fp.write(self.escape)
				self.__fp.write(self.insert)
				self.__fp.write('''					
					while (1) {
				''')
				self.alts(part.alts)
				self.__fp.write('''
						tmp = pop();					
						if (tmp) {
				''')
				self.__fp.write(self.insert)
				self.__fp.write('''
						}
						else break;
					}
				''')
				
			elif part.op == "?":
				self.alts(part.alts)
				self.__fp.write('''
					tmp = pop();					
					if (tmp) {
				''')
				self.__fp.write(self.insert)
				self.__fp.write('''
					}
				''')
				
			elif part.op == "*":
				self.__fp.write('''					
					while (1) {
				''')
				self.alts(part.alts)
				self.__fp.write('''
						tmp = pop();					
						if (tmp) {
				''')
				self.__fp.write(self.insert)
				self.__fp.write('''
						}
						else break;
					}
				''')
			
			self.__fp.write(f'''
				// END WILDCARD {part.op} : {part.alts}
			''')
	
		if isinstance(part, Charset):
			symbol = f'''
				ctmp = symbol(
					{part.chars}, 
					{len(part.chars) - 2}
				);
			'''
						
			self.__fp.write(symbol)
			
			if part.op == "":
				self.__fp.write(self.cescape)
				self.__fp.write(self.mkstr)
				
			elif part.op == "+":
				self.__fp.write(self.cescape)
				self.__fp.write(self.mkstr)
				self.__fp.write(f'''
					while (ctmp) {{
						{symbol}
						
						if (ctmp) {{
							{self.addchr}
						}}
						else break;
					}}
				''')
				
			elif part.op == "?":
				self.__fp.write(f'''
					if (ctmp) {{
						{self.mkstr}
					}}
				''')
				
			elif part.op == "*":
				self.__fp.write(f'''
					if (ctmp) {{
						{self.mkstr}
					}}
				
					while (ctmp) {{
						{symbol}
						
						if (ctmp) {{
							{self.addchr}
						}}
						else break;
					}}
				''')
							
	def alt(self, alt):
		self.__fp.write(f'''
			top() = new Node{{}};
		''')
		
		for part in alt:
			self.part(part)
	
	def alts(self, alts):
		self.depth += 1
		
		self.__fp.write(f'''
			// ALTS {alts}
			push(nullopt);
		''')
		
		for alt in alts:
			self.__fp.write(f'''
				// ALT {alt}
				while (!top()) {{
					mark();
			''')
			
			self.alt(alt)
			
			self.__fp.write(f'''
					unmark();
				}}
				// END ALT {alt} 
			''')
		
		self.__fp.write(f'''
			// END ALTS {alts}
			assert(results.size() == init_size + {self.depth});
		''')
		
		self.depth -= 1
	
	def generate(self):
		self.__fp.write(self.class_header)
		
		for rule in self.__grammar:
			self.__fp.write(f'''
				optional<Node*> parse{rule.name}() {{
					const size_t init_size = results.size();
					
					optional<Node*> tmp = nullopt;
					optional<char> ctmp = nullopt;
			''')
			
			self.alts(rule.alts)
			
			self.__fp.write(f'''
					tmp = pop();
					if (tmp) {{
						(*tmp)->data = "{rule.name}";
					}}
					
					return tmp;
				}}
			''')
		
		self.__fp.write("};")

import sys

if __name__ == "__main__":
	if len(sys.argv) != 3:
		print(f"Usage: {sys.argv[0]} GRAMMAR_FILE HEADER_FILE")
		print("Takes BNF grammar in GRAMMAR_FILE")
		print("And generates C++ parser in HEADER_FILE")
		
		exit(0)
	
	with open(sys.argv[1], "rb") as fin:
		parser = GrammarParser(fin)
		grammar = parser.parseGrammar()

	print("Parsed grammar:")
	print(grammar)

	with open(sys.argv[2], "w") as fout:
		generator = PEGGenerator(grammar, fout)
		generator.generate()


