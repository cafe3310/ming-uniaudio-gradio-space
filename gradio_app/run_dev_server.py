import watchfiles
import logging
import sys

# Configure logging to provide feedback on the watcher's status
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    """
    This script uses 'watchfiles' to monitor for file changes in the current
    directory (and subdirectories) and automatically restarts the Gradio
    application.

    It's a convenient way to develop without manually stopping and restarting
    the server after each code change.

    To run:
        python run_dev_server.py
    """
    logging.info("Starting file watcher and development server for app.py...")
    
    # run_process will watch for changes in the current path ('.')
    # and restart the target command.
    watchfiles.run_process(
        '.',  # Watch the current directory
        target=f'{sys.executable} app.py --color',  # Command to run
        target_type='command',
        debounce=2_000,
        step=1_000,
        sigint_timeout=1,
    )
