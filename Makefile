CC = g++
FLAGS = -fsanitize=address --std=c++17
PY = python3
FMT = clang-format
DOT = dot

all:
	$(PY) peggen.py lang_grammar genParser.hpp
	$(FMT) genParser.hpp > Parser.hpp
	rm genParser.hpp
	$(CC) $(FLAGS) main.cpp -o test
