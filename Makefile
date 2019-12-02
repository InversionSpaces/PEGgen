CC = g++
FLAGS = -fsanitize=address --std=c++17
PY = python3
FMT = clang-format
DOT = dot


all: gen	
	$(CC) $(FLAGS) testf.cpp -o testb

gen:
	$(PY) Parser.py
	$(FMT) test.cpp > testf.cpp

run: all
	./testb
	
show:
	$(DOT) -Tpng dump.dot -o /tmp/dump.png
	xdg-open /tmp/dump.png
