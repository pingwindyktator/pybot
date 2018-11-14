from __future__ import print_function

import sys
import traceback
import os
import backtracepython


def main():
    backtracepython.initialize(
        endpoint="https://submit.backtrace.io/pingwindyktator/1ce98b24c4b29dd8b7f3c84599a5b7a7564fed071c441960a791fd638c3f7335/json",
        token="1ce98b24c4b29dd8b7f3c84599a5b7a7564fed071c441960a791fd638c3f7335"
    )

    import _main
    _main.main(debug_mode=False)


if __name__ == "__main__":
    if sys.version_info < (3, 6, 0):
        print('Python 3.6.0 required to run pybot')
        sys.exit(4)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    try:
        main()

    except (ImportError, ModuleNotFoundError) as e:
        name = e.name
        path = ' located at %s' % e.path if e.path else ''
        print("No module named %s%s. Please try 'pip install -r requirements.txt'" % (name, path))

    except Exception as e:
        print()
        print('Internal error occurred: %s: %s' % (type(e).__name__, e))
        print('Please contact  ja2222ja@gmail.com  with  pybot.error  file (file paths will be compromised)')

        try:
            backtracepython.send_last_exception()
        except Exception as e:
            print('Unable to report error to backtrace.io')

        open('pybot.error', 'w').close()
        if not os.path.exists('pybot.log'):
            open('pybot.log', 'w').close()

        with open('pybot.error', 'a') as error_file:
            with open('pybot.log') as log_file:
                error_file.writelines(log_file.readlines()[-300:])

            error_file.write('\n')
            error_file.write(traceback.format_exc())
            error_file.write('**********************************************************************************************\n\n')
