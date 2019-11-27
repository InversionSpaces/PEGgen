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

Rule = namedtuple("Rule", ["name", "alts"])

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

Wildcard = namedtuple("Wildcard", ["op", "alts"])

class GrammarParser(Parser):
	
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
					self.parseWildcard()	)
					
		if not token:
			return None
		
		alt = [token]
		while True:
			token = (	self.expect(NAME) or 
						self.expect(STRING)	or
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
	
	class_header = '''
	#include <cstring>
	#include <string>
	#include <iostream>
	#include <stack>
	
	using namespace std;

	class Parser
	{
	private:
		const char* input;
		stack<const char*> marks;
		stack<int> results;
	public:
		Parser(const char* input) : input(input)
		{
		}
		
		inline void skip()
		{
			while (isspace(*input)) input++;
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
		
		inline int pop()
		{
			int retval = results.top();
			results.pop();
			return retval;
		}
		
		inline void push(int res)
		{
			results.emplace(res);
		}
		
		inline void drop()
		{
			int temp = results.top();
			results.pop();
			results.top() = temp;
		}
		
		inline int& top()
		{
			return results.top();
		}
		
		const char* pos()
		{
			return input;
		}
		
		int expect(const char* s, int n)
		{
			skip();
			if (strncmp(input, s, n) == 0) {
				input += n;
				return 1;
			}
			return 0;
		}
	'''
	
	class_footer = '''
		};
		
		int main() {
			string s;
			getline(cin, s);
			Parser p(s.c_str());
			cout << p.parseE() << endl;
			cout << p.pos() << endl;
		}
	'''
	
	escape = '''
		if (!top()) {
			reset();
			break;
		}
	'''
	
	def part(self, part):
		if isinstance(part, Token):
			if part.type == STRING:
				self.__fp.write(f'''
					top() = expect({part.str}, {len(part.str) - 2});
				''')
				
			elif part.type == NAME:
				self.__fp.write(f'''
					top() = parse{part.str}();
				''')
				
			self.__fp.write(self.escape)
				
		if isinstance(part, Wildcard):		
			self.alts(part.alts)
			
			if part.op == "":
				self.__fp.write('''
					drop();
				''')
				
			elif part.op == "+":
				self.__fp.write(self.escape)
				self.__fp.write('''
					push(top());
					while (top()) {
				''')
				self.alts(part.alts)
				self.__fp.write('''
						drop();
					}
					pop();
				''')
				
			elif part.op == "?":
				self.__fp.write('''
					pop();
				''')
				
			elif part.op == "*":
				self.__fp.write('''
					push(top());
					while (top()) {
				''')
				self.alts(part.alts)
				self.__fp.write('''
						drop();
					}
					pop();
				''')
	
	def alt(self, alt):
		for part in alt:
			self.part(part)
	
	def alts(self, alts):
		self.__fp.write('''
			push(0);
		''')
		
		for alt in alts:
			self.__fp.write('''
				while (!top()) {
					mark();
			''')
			
			self.alt(alt)
			
			self.__fp.write('''
					unmark();
				}
			''')
	
	def generate(self):
		self.__fp.write(self.class_header)
		
		for rule in self.__grammar:
			self.__fp.write(f'''
				int parse{rule.name}() {{
			''')
			
			self.alts(rule.alts)
			
			self.__fp.write('''
					return pop();
				}
			''')
		
		self.__fp.write(self.class_footer)

fin = open("test", "rb")

parser = GrammarParser(fin)

fout = open("test.cpp", "w")

grammar = parser.parseGrammar()

fin.close()

print(grammar)

generator = PEGGenerator(grammar, fout)

generator.generate()

fout.close()


