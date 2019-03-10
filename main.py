# noinspection PyUnresolvedReferences
import __future__
import sys
import os
import platform


def main():
    import _main
    _main.main(debug_mode=False)


if __name__ == "__main__":
    if sys.version_info < (3, 6, 0):
        print('Python >= v3.6.0 required to run pybot, you have %s' % platform.python_version())
        sys.exit(4)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    try:
        main()

    except (ImportError, ModuleNotFoundError) as e:
        name = e.name
        path = ' located at %s' % e.path if e.path else ''
        err_msg = 'No module named %s%s' % (name, path) if name else str(e).capitalize()
        print("%s, please try 'pip install -r requirements.txt'" % err_msg)

    except Exception as e:
        print()
        print('Internal error occurred: %s: %s' % (type(e).__name__, e))

        try:
            import sentry_sdk
            sentry_sdk.capture_exception()
            print('Error report sent to sentry.io')
        except Exception as e:
            print('Unable to report error to sentry.io: %s: %s' % (type(e).__name__, e))
            print('Please contact  ja2222ja@gmail.com  with  pybot.error  file (file paths will be compromised)')

        try:
            import traceback
            open('pybot.error', 'w').close()
            if not os.path.exists('pybot.log'):
                open('pybot.log', 'w').close()

            with open('pybot.error', 'a') as error_file:
                with open('pybot.log') as log_file:
                    error_file.writelines(log_file.readlines()[-300:])

                error_file.write('\n')
                error_file.write(traceback.format_exc())
                error_file.write('**********************************************************************************************\n\n')
        except Exception as e:
            print('Unable to prepare pybot.error report: %s: %s' % (type(e).__name__, e))
