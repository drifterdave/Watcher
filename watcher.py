import sys
import time
import shlex
import argparse
import pyinotify
import subprocess

import logging
import logging.handlers as handlers

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

OLDDIR = args['source_directory'].rstrip('/')
NEWDIR = args['target_directory'].rstrip('/')

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


# Begin Watching for Files
watcher.info("Watches established.")

wm = pyinotify.WatchManager()
# noinspection PyUnresolvedReferences
mask = pyinotify.IN_MOVED_TO


class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CLOSE_WRITE(self, event):
        watcher.debug(event)
        to_folder = event.path.replace(OLDDIR, NEWDIR) + '/'
        watcher.info('Syncing change: {}'.format(event.pathname))
        command = 'rsync -PvarH {} {}'.format(event.pathname, to_folder).replace("'", r"\'").replace("&", r"\&")
        if not args['no_tmux']:
            command = 'tmux send-keys -t rsync "{}" c-m'.format(command.replace(' ', r' '))

        watcher.info('Running command: {}'.format(command))
        time.sleep(10)  # Sleep to wait for Sonarr to apply permissions...
        subprocess.Popen(shlex.split(command), stdin=None, stdout=None, stderr=None)

    def process_IN_MOVED(self, event):
        self.process_IN_CLOSE_WRITE(event)

    def process_default(self, event):
        watcher.debug(event)


notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
notifier.start()

wdd = wm.add_watch(OLDDIR, mask, rec=True)