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
	#include <cassert>
	
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
			while (*input && isspace(*input)) input++;
		}
		
		inline int symbol(const char* c, size_t n)
		{
			skip();
			if (*input && strchr(c, *input) != NULL) {
				input++;
				return 1;
			}
			return 0;
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
			cout << p.parseE() << ": |" <<p.pos() << "|" << endl;
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
			self.__fp.write(f'''
				// WILDCARD {part.op} : {part.alts}
			''')
				
			if part.op == "":
				self.alts(part.alts)
				self.__fp.write('''
					drop();
				''')
				self.__fp.write(self.escape)
				
			elif part.op == "+":
				self.alts(part.alts)
				self.__fp.write('''
					drop();
				''')
				self.__fp.write(self.escape)
				self.__fp.write('''
					do {
				''')
				self.alts(part.alts)
				self.__fp.write('''
					} while (pop());
					top() = 1;
				''')
				
			elif part.op == "?":
				self.alts(part.alts)
				self.__fp.write('''
					pop();
					top() = 1;
				''')
				
			elif part.op == "*":
				self.__fp.write('''
					do {
				''')
				self.alts(part.alts)
				self.__fp.write('''
					} while (pop());
					top() = 1;
				''')
			
			self.__fp.write(f'''
				// END WILDCARD {part.op} : {part.alts}
			''')
	
		if isinstance(part, Charset):
			symbol = f'''
				top() = symbol(
					{part.chars}, 
					{len(part.chars) - 2}
				);
			'''
			
			skip = f'''
				do {{
					push(0);
					{symbol}
				}} while (pop());
			'''
			
			self.__fp.write(symbol)
			
			if part.op == "":
				self.__fp.write(self.escape)
				
			if part.op == "+":
				self.__fp.write(self.escape)
				self.__fp.write(skip)
				
			if part.op == "?":
				self.__fp.write(f'''
					top() = 1;
				''')
				
			if part.op == "*":
				self.__fp.write(skip)
				self.__fp.write('''
					top() = 1;
				''')
				
			
	def alt(self, alt):
		for part in alt:
			self.part(part)
	
	def alts(self, alts):
		self.depth += 1
		
		self.__fp.write(f'''
			// ALTS {alts}
			push(0);
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
			cout << init_size << " : " << results.size() << endl;
			assert(results.size() == init_size + {self.depth});
		''')
		
		self.depth -= 1
	
	def generate(self):
		self.__fp.write(self.class_header)
		
		for rule in self.__grammar:
			self.__fp.write(f'''
				int parse{rule.name}() {{
					cout << "Start parse {rule.name}" << endl;
					const size_t init_size = results.size();
			''')
			
			self.alts(rule.alts)
			
			self.__fp.write(f'''
					cout << "End parse {rule.name}" << endl;
					return pop();
				}}
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


