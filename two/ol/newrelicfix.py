import os
import sys

_commands = {}

initialized = False

def MiddleWare():
    global initialized

    if initialized:
        return

    initialized = True
    import newrelic.agent
    from django.conf import settings


    config_file = settings.NEW_RELIC_CONFIG_FILE
    environment = settings.NEW_RELIC_ENVIRONMENT

    # import pdb; pdb.set_trace()
    
    newrelic.agent.initialize(config_file, environment)

def main():
    try:
        import newrelic
    except ImportError:
        print >> sys.stderr, "newrelic is not installed"
        sys.exit(0)

    admin = os.path.join(os.path.dirname(newrelic.__file__), '..', "EGG-INFO",'scripts',  "newrelic-admin")
    
    execfile(admin, {'__name__':'__main__'})
    # import pdb; pdb.set_trace()
    


