import sys
import shlex
import pexpect
import argparse
import subprocess

import logging
import logging.handlers as handlers

from datetime import datetime
from StringIO import StringIO
from csv import reader

parser = argparse.ArgumentParser(description='Watches a directory for changes, then syncs those changes to another '
                                             'directory.')
parser.add_argument('-s', '--source-directory', help='Path you want to watch for changes.', required=True)
parser.add_argument('-t', '--target-directory', help='Path you want to sync changes to.', required=True)
parser.add_argument('-l', '--log-file', help='Path to where you want the log files kept.', default='FileSyncDebug.log')
parser.add_argument('--debug', help='Output debug logs to stdout.', action='store_true', default=False)
parser.add_argument('--no-tmux', help="Don't send command to a tmux session named 'tmux', just run it. (Caution, this "
                                      "causes the output for the rsync command to go to stdout)",
                    action='store_true', default=False)

group = parser.add_mutually_exclusive_group()
group.add_argument('--no-log-file', help='Disables the log file.', action='store_true', default=False)
group.add_argument('--quiet', help='Supresses STDOUT output.', action='store_true', default=False)

args = vars(parser.parse_args())

OLDDIR = args['source_directory']
NEWDIR = args['target_directory']

watcher = logging.getLogger()
watcher.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')

if not args['no_log_file']:
    logfile = handlers.TimedRotatingFileHandler(filename=args['log_file'], when='midnight', backupCount=10)
    logfile.setLevel(logging.DEBUG)
    logfile.setFormatter(formatter)
    watcher.addHandler(logfile)

if not args['quiet']:
    stdout = logging.StreamHandler(sys.stdout)
    if args['debug']:
        stdout.setLevel(logging.DEBUG)
    else:
        stdout.setLevel(logging.INFO)
    stdout.setFormatter(formatter)
    watcher.addHandler(stdout)





watcher.info("Executing watcher: inotifywait -r " + OLDDIR + " --event moved_to,close_write -m -c")

inotify = pexpect.spawn('inotifywait -r ' + OLDDIR + ' --event moved_to,close_write -m -c')

inotify.expect('Setting up watches.  Beware: since -r was given, this may take a while!\r\n', timeout=None)
watcher.info("Watcher is initializing.")
inotify.expect('Watches established.\r\n', timeout=None)
# Begin Watching for Files



last = 'Initial'

lasttime = datetime.now()
watcher.info("Watches established.")
while True:
    inotify.expect('\r\n', timeout=None)
    event = inotify.before
    watcher.debug(event)
    output = reader(StringIO(event)).next()  # This will work until I get pyinotify working.
    watcher.debug(output)
    name = output[0] + output[-1]
    folder = output[0].replace(OLDDIR, NEWDIR)
    delta = datetime.now() - lasttime
    if (last not in name) or delta.seconds > 60:
        watcher.info('Syncing change: {}'.format(name))
        last = name
        lasttime = datetime.now()

        command = 'rsync -PvarH {} {}'.format(name, folder).replace("'", r"\'").replace("&", r"\&")
        if not args['no_tmux']:
            command = 'tmux send-keys -t rsync "{}" c-m'.format(command.replace(' ', r' '))

        watcher.info('Running command: {}'.format(command))

        subprocess.Popen(shlex.split(command), stdin=None, stdout=None, stderr=None)
    else:
        watcher.debug('We just saw "{}, {} seconds ago, skipping."'.format(last, delta.seconds))
