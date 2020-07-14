CC = g++
FLAGS = -fsanitize=address --std=c++17
PY = python3
FMT = clang-format
DOT = dot

all:
	$(PY) -m peggen lang_grammar header.hpp
	$(CC) $(FLAGS) test.cpp -o test
	./test < prog.cn > prog.dot
	$(DOT) -Tpng prog.dot > prog.png
