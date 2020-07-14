from tokenize import tokenize, NAME, STRING, NEWLINE
from io import BytesIO
from collections import namedtuple

Token = namedtuple("Token", ["type", "str"])


class Tokenizer:
    def __init__(self, fp):
        self.__tokenizer = tokenize(fp.readline)
        self.__tokens = list()
        self.__pos = 0

        try:
            next(self.__tokenizer)  # To skip encoding
        except StopIteration:
            pass

    def get_pos(self):
        return self.__pos

    def set_pos(self, pos):
        self.__pos = pos

    def get_token(self):
        token = self.peek_token()
        if (token):
            self.__pos += 1
        return token

    def peek_token(self):
        if self.__pos < len(self.__tokens):
            return self.__tokens[self.__pos]

        try:
            token = Token(*next(self.__tokenizer)[:2])
            self.__tokens.append(token)
            return token
        except StopIteration:
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
        return None


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
        token = (self.expect(NAME) or
                 self.expect(STRING) or
                 self.parseCharset() or
                 self.parseWildcard())

        if not token:
            return None

        alt = [token]
        while True:
            token = (self.expect(NAME) or
                     self.expect(STRING) or
                     self.parseCharset() or
                     self.parseWildcard())

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
