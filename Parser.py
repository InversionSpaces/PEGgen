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
	#include <iostream>
	#include <stack>
	
	using namespace std;

	class Parser
	{
	private:
		const char* input;
		stack<const char*> marks;
	public:
		Parser(const char* input) : input(input)
		{
		}
		
		void skip()
		{
			while (isspace(*input)) input++;
		}
		
		void reset()
		{
			input = marks.top();
			marks.pop();
		}	
		
		void mark()
		{
			marks.push(input);
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
	
	def part(self, part):
		if isinstance(part, Token):
			if part.type == STRING:
				self.__fp.write(f'''
					res = expect({part.str}, {len(part.str) - 2});
					if (!res) {{
						reset();
						break;
					}}
				''')
			elif part.type == NAME:
				self.__fp.write(f'''
					res = parse{part.str}();
					if (!res) {{
						reset();
						break;
					}}
				''')
				
		if isinstance(part, Wildcard):
			if part.op == "":
				for alt in part.alts:
					self.alt(alt)
					self.__fp.write('''
					if (!res) {{
						reset();
						break;
					}}
					''')
			elif part.op == "+":
				pass
			elif part.op == "?":
				pass
			elif part.op == "*":
				pass
	
	def alt(self, alt):
		for part in alt:
			self.part(part)
	
	def rule(self, rule):
		for alt in rule.alts:
			self.__fp.write('''
				while (!res) {
					mark();
			''')
			self.alt(alt)
			self.__fp.write('''}''')
	
	def generate(self):
		self.__fp.write(self.class_header)
		
		for rule in self.__grammar:
			self.__fp.write(f'''
				int parse{rule.name}() {{
					int res = 0;
			''')
			self.rule(rule)
			self.__fp.write('''
				return res;
				}
			''')
		
		self.__fp.write('''
			};
			
			int main() {
				Parser p("");
				cout << p.parseE() << endl;
				cout << p.pos() << endl;
			}
		''')

fin = open("test", "rb")

parser = GrammarParser(fin)

fout = open("test.cpp", "w")

grammar = parser.parseGrammar()

fin.close()

print(grammar)

generator = PEGGenerator(grammar, fout)

generator.generate()

fout.close()


