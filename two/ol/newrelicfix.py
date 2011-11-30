import os
import sys

_commands = {}

def main():
    try:
        import newrelic
    except ImportError:
        print >> sys.stderr, "newrelic is not installed"
        sys.exit(0)

    admin = os.path.join(os.path.dirname(newrelic.__file__), '..', "EGG-INFO",'scripts',  "newrelic-admin")
    
    execfile(admin, {'__name__':'__main__'})
    # import pdb; pdb.set_trace()
    


