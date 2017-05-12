import sys


def main():
    if sys.version_info < (3, 6, 0):
        print("Python 3.6.0 required to run pybot")
        sys.exit(4)

    import _main
    _main.main()

if __name__ == "__main__":
    main()
