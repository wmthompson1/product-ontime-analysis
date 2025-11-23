import sys

sys.stderr.write('This is sample error.')
sys.stderr.flush()

sys.stdout.write(
    "This is regular text being delivered directly to the terminal.")

if len(sys.argv) > 1:
    print(sys.argv[1])

if len(sys.argv) > 1:
    print(float(sys.argv[1]) + 10)
