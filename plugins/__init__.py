from os.path import dirname, basename, isfile
import glob

__MODULES = glob.glob(dirname(__file__) + "/*.py")
__all__ = [basename(f)[:-3] for f in __MODULES if isfile(f)]
