import warnings


def ignore():
    """Suppresses some warnings of praw."""
    warnings.filterwarnings('ignore', 'The keyword `bot` in your user_agent may be problematic.')
    # And the socket gets closed.
    warnings.filterwarnings('ignore', 'unclosed*')
