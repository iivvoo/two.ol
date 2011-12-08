import os
import sys

_commands = {}

def runner():
    try:
        config_file = os.environ.get('NEW_RELIC_CONFIG_FILE')
        environment = os.environ.get('NEW_RELIC_ENVIRONMENT')

        import newrelic.agent

        newrelic.agent.initialize(config_file, environment)
        print "New Relic agent initialized"
        print "  config     : %s" % config_file
        print "  environment: %s" % environment

    except ImportError:
        print >> sys.stderr, "New Relic module not installed"
    execfile("bin/django", {'__name__':'__main__'})

def main():
    try:
        import newrelic
    except ImportError:
        print >> sys.stderr, "newrelic is not installed"
        sys.exit(0)

    admin = os.path.join(os.path.dirname(newrelic.__file__), '..', "EGG-INFO",'scripts',  "newrelic-admin")
    
    execfile(admin, {'__name__':'__main__'})
    


