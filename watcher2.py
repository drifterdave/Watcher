import pexpect
import subprocess
from datetime import datetime
import time
import logging
import sys

#inotifywait -r /nas/test --event moved_to,close_write -m -c


root = logging.getLogger()
root.setLevel(logging.DEBUG)
stdout = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout.setFormatter(formatter)
root.addHandler(stdout)



inotify = pexpect.spawn('inotifywait -r /nas/test1 --event moved_to,close_write -m -c')

inotify.expect('Setting up watches.  Beware: since -r was given, this may take a while!\r\n', timeout=None)
inotify.expect('Watches established.\r\n', timeout=None)
# Begin Watching for Files



last = 'Initial'

lasttime = datetime.now()
time.sleep(5)
root.info("Watching for new files")
while True:
    inotify.expect('\r\n', timeout=None)
    output = inotify.before.split(',')
    name = output[0] + output[-1]
    root.info('Caught change: {}'.format(name))
    delta = datetime.now() - lasttime
    if delta.seconds > 5:
        lasttime = datetime.now()
        last = name
        if 'rsync -varH' and 'sleep' and 'tmux send-keys' not in subprocess.check_output(["ps", "-ef"]):
            root.info('Running rsync for file: {}'.format(name))
            subprocess.Popen(['tmux', 'send-keys', '-t', 'rsync', 'rsync ', '-PvarH ', '/nas/test1/* ', '/nas/test2/ ',
                              'c-m'], stdin=None, stdout=None, stderr=None)
        else:
            root.warning('rsync already running for {}.'.format(last))
    else:
        root.warning('We just saw "{}, {} seconds ago"'.format(last, delta.seconds))