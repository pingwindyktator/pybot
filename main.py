from __future__ import print_function
import sys
import traceback
import os


def main():
    import _main
    _main.main(debug_mode=False)


if __name__ == "__main__":
    if sys.version_info < (3, 6, 0):
        print('Python 3.6.0 required to run pybot')
        sys.exit(4)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    try:
        main()

    except KeyboardInterrupt:
        try: sys.exit(0)
        except SystemExit: os._exit(0)

    except (ImportError, ModuleNotFoundError) as e:
        name = e.name
        path = ' located at %s' % e.path if e.path else ''
        print("No module named %s%s. Please try 'pip install -r requirements.txt'" % (name, path))

    except Exception as e:
        print('\nInternal error occurred: %s: %s\nPlease contact  ja2222ja@gmail.com  with  pybot.error  file (file paths will be compromised).'
              % (type(e).__name__, e))
        open('pybot.error', 'w').close()
        with open('pybot.error', 'a') as error_file:
            with open('pybot.log') as log_file:
                error_file.writelines(log_file.readlines()[-300:])

            error_file.write('\n')
            error_file.write(traceback.format_exc())
            error_file.write('**********************************************************************************************\n\n')
