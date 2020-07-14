CC = g++
FLAGS = -fsanitize=address --std=c++17
PY = python3
FMT = clang-format
DOT = dot

all:
	$(PY) peggen.py lang_grammar header.hpp
	$(CC) $(FLAGS) test.cpp -o test
	./test < prog.cn > prog.dot
	$(DOT) -Tpng prog.dot > prog.png
	diff prog.png etalon.png
