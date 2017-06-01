import sys
import traceback


def main():
    import _main
    _main.main()


if __name__ == "__main__":
    if sys.version_info < (3, 6, 0):
        print("Python 3.6.0 required to run pybot")
        sys.exit(4)

    try:
        main()
        open('pybot.error', 'w').close()
    except (ImportError, ModuleNotFoundError) as e:
        name = e.name
        path = ' located at %s' % e.path if e.path else ''
        print("No module named %s%s. Please try 'pip install -r ./requirements.txt'" % (name, path))
    except Exception as e:
        print('Internal error occurred: %s. Please contact  ja222ja@gmail.com  with  pybot.error  file (file paths will be compromised).' % e)
        open('pybot.error', 'w').close()
        with open('pybot.error', 'a') as error_file:
            with open('pybot.log') as log_file:
                error_file.writelines(log_file.readlines()[-300:])

            error_file.write('\n')
            error_file.write(traceback.format_exc())
            error_file.write('**********************************************************************************************\n\n')
