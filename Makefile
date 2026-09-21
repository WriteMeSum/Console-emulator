CXX = clang++
CXXFLAGS = -std=c++20 -Wall -Wextra -Isrc
LDFLAGS = -framework Cocoa

.PHONY: all run test clean create-vfs

all: emulator run_tests

emulator: src/main.mm src/parser.cpp src/vfs.cpp src/shell.cpp
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS) -lz

run_tests: tests/test_main.cpp src/parser.cpp src/vfs.cpp src/shell.cpp
	$(CXX) $(CXXFLAGS) $^ -o $@ -lz

create-vfs:
	python3 tests/create_test_vfs.py

run: emulator create-vfs
	./emulator --vfs test_vfs.zip --script scripts/start.txt

test: run_tests create-vfs
	./run_tests

clean:
	rm -rf emulator run_tests test_vfs.zip test_temp.zip
