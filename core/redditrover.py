# coding=utf-8
from configparser import ConfigParser
from time import time, sleep, strptime
from sys import exit
import pkgutil
import traceback

from pkg_resources import resource_filename
from praw.exceptions import *
import praw

import plugins
from core import logprovider
from misc import warning_filter
from core import *
from .decorators import retry
from core.stats import StatisticsFeeder


class RedditRover:
    """
    Reddit Rover object is the full framework. When initing, it reads all plugins, initializes them and starts loading
    submissions and comments from Reddit. Varying from your implementation, it will fire those submissions and comments
    to your bot. Based on the configuration setting the bot will run a maintenance and update procedure, cleaning up
    the database and rolling over submissions / comments of a plugin which requested to update from there out on.


    :ivar logger: Central bot logger.
    :vartype logger: Logger
    :type logger: logging.Logger
    :ivar config: Holds a full set of configs from the configfile.
    :vartype config: ConfigParser
    :type config: ConfigParser
    :ivar responders: A list of plugins the bot is running. @TODO: Exit the bot if no plugin is found.
    :vartype responders: list
    :type responders: list
    :ivar multi_thread: The MultiThreader instance, which manages daemonic threads.
    :vartype multi_thread: MultiThreader
    :type multi_thread: MultiThreader
    :ivar delete_after: All activity older than x seconds will be cleaned up from the database.
    :vartype delete_after: int
    :type delete_after: int
    :ivar verbose: True if heavily verbose, false if not.
    :vartype verbose: bool
    :type verbose: bool
    :ivar update_interval: Sets an interval on the update-thread, cleaning the DB, reading messages and running updates
    :vartype update_interval: int
    :type update_interval: int
    :ivar catch_http_exception: True if HTTP exceptions get automatically catched, False if not.
    :vartype catch_http_exception: bool
    :type catch_http_exception: bool
    :ivar mark_as_read: True if all messages worked through are marked as read.
    :vartype mark_as_read: bool
    :type mark_as_read: bool
    :ivar praw_handler: Will hold the handler to RateLimit based on OAuth / No-Auth sessions.
    :vartype praw_handler: RedditRoverHandler
    :type praw_handler: RedditRoverHandler
    :ivar submission_poller: Anonymous reddit session for submissions.
    :vartype submission_poller: praw.Reddit
    :type submission_poller: praw.Reddit
    :ivar submissions: Generator of recent submissions on Reddit.
    :vartype submissions: praw.helpers.comment_stream
    :type submissions: praw.helpers.comment_stream
    :ivar comments: Generaot of recent comments on Reddit.
    :vartype comments: praw.helpers.comment_stream
    :type comments: praw.helpers.comment_stream
    """

    def __init__(self):
        warning_filter.ignore()
        self.config = ConfigParser()
        self.config.read(resource_filename('config', 'bot_config.ini'))
        self.mark_as_read, self.catch_http_exception, self.delete_after, self.verbose, self.update_interval, \
            subreddit, generate_stats, www_path = self._bot_variables()
        self.logger = logprovider.setup_logging(log_level=("DEBUG", "INFO")[self.verbose],
                                                web_log_path='log.log')
        self.multi_thread = MultiThreader()
        self.lock = self.multi_thread.get_lock()
        self.database_update = Database()
        self.database_cmt = Database()
        self.database_subm = Database()

        try:
            self.praw_handler = RoverHandler()
            self.responders = []
            self.load_responders()
            self.submission_poller = praw.Reddit(
                user_agent=self.config.get("SUBMISSION_BOT", "description"),
                client_id=self.config.get("SUBMISSION_BOT", "app_key"),
                client_secret=self.config.get("SUBMISSION_BOT", "app_secret"),
                refresh_token=self.config.get("SUBMISSION_BOT", "refresh_token")
            )
        except Exception as e:  # I am sorry linux, but ConnectionRefused Error can't be imported.
            self.logger.error(e)
            self.logger.error(traceback.print_exc())
            exit(-1)
        if generate_stats:  # Not everyone hosts a webserver, not everyone wants stats.
            self.stats = StatisticsFeeder(self.database_update, self.praw_handler, www_path)
        else:
            self.stats = None

        self.sub = self.submission_poller.subreddit(subreddit)
        self.submissions = self.sub.stream.submissions(pause_after=-1)
        self.comments = self.sub.stream.comments(pause_after=-1)
        self.multi_thread.go([self.comment_thread], [self.submission_thread], [self.update_thread])
        self.multi_thread.join_threads()

    def _bot_variables(self):
        """
        Gets all relevant variables for this bot from the configuration
        :return: Tuple of ``(mark_as_read, catch_http_exception, delete_after, verbose, subreddit)``
        """
        get_b = lambda x: self.config.getboolean('RedditRover', x)
        get_i = lambda x: self.config.getint('RedditRover', x)
        get = lambda x: self.config.get('RedditRover', x)
        return get_b('mark_as_read'), get_b('catch_http_exception'), get_i('delete_after'), get_b('verbose'),\
            get_i('update_interval'), get('subreddit'), get_b('generate_stats'), get('www_path')


    # TODO: fix this function, always returns false, breaking the program
    def _filter_single_thing(self, thing, responder):
        """
        Helper method to filter out submissions, returns `True` or `False` depending if it hits or fails.

        :param thing: Single submission or comment
        :type thing: praw.models.reddit.comment.Comment | praw.models.reddit.submission.Submission
        :param responder: Single plugin
        :type responder: PluginBase
        """
        # noinspection PyBroadException
        try:
            if isinstance(thing, praw.models.reddit.comment.Comment):
                db = self.database_cmt
            else:
                db = self.database_subm
            b_name = responder.BOT_NAME
            if db.retrieve_thing(thing.name, b_name):
                return False
            if hasattr(thing, 'author') and type(thing.author) is praw.models.Redditor:
                if db.check_user_ban(thing.author.name, b_name):
                    return False
                if thing.author.name == responder.session.user.name and hasattr(responder, 'SELF_IGNORE') and \
                        responder.SELF_IGNORE:
                    return False
            if hasattr(thing, 'subreddit') and db.check_subreddit_ban(thing.subreddit.display_name, b_name):
                return False
            return True
        except Exception:
            return False

    def load_responders(self):
        """
        Loads all plugins from ./plugins/, appends them to a list of responders and verifies that they're properly setup
        and working for the main bot process.
        """
        # cleaning of the list
        self.responders = []
        # preparing the right sub path.
        package = plugins
        prefix = package.__name__ + "."

        # we're running through all
        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix):
            module = __import__(modname, fromlist="dummy")
            # every sub module has to have an object provider,
            # this makes importing the object itself easy and predictable.
            module_object = module.init(Database(), None)
            try:
                if not isinstance(module_object, PluginBase):
                    raise ImportError('Module {} does not inherit from PluginBase class'.format(
                        module_object.__class__.__name__))
                # could / should fail due to variable validation
                # (aka: is everything properly set to even function remotely.)
                module_object.integrity_check()
                self.database_update.register_module(module_object.BOT_NAME)
                self.logger.info('Module "{}" is initialized and ready.'.format(module_object.__class__.__name__))
            except Exception as e:
                # Catches _every_ error and skips the module. The import will now be reversed.
                self.logger.error(traceback.print_exc())
                self.logger.error("{}: {}".format(module_object.__class__.__name__, e))
                del module, module_object
                continue
            # If nothing failed, it's fine to import.
            self.responders.append(module_object)
        if len(self.responders) == 0:
            self.logger.info('No plugins found and / or working, exiting RedditRover.')
            sys.exit(0)
        self.logger.info("Imported a total of {} object(s).".format(len(self.responders)))

    def submission_thread(self):
        """
        The submission thread runs down all submission from the specified sub (usually /r/all),
        then filters out all banned users and subreddits and then fires submissions at your plugins.
        """
        self.logger.info("Opened submission stream successfully.")
        for subm in self.submissions:
            if subm is not None:
                self.comment_submission_worker(subm)
                self.database_subm.add_submission_to_meta(1)

    def comment_thread(self):
        """
        The comment thread runs down all comments from the specified sub (usually /r/all),
        then filters out banned users and subreddits and fires it at your plugins.
        """
        self.logger.info("Opened comment stream successfully.")
        for comment in self.comments:
            if comment is not None:
                self.comment_submission_worker(comment)
                self.database_cmt.add_comment_to_meta(1)

    def comment_submission_worker(self, thing):
        """
        Runs through all available plugins, filters them based on that out and calls the right method within a plugin.

        :param thing: Single submission or comment
        :type thing: praw.models.reddit.comment.Comment | praw.models.reddit.submission.Submission
        """
        for responder in self.responders:
            # Check beforehand if a subreddit or a user is banned from the bot / globally.
            # if self._filter_single_thing(thing, responder):
            try:
                self.comment_submission_action(thing, responder)
            except PRAWException as e:
                if self.catch_http_exception:
                    self.logger.error('{} encountered: PRAWException - probably Reddits API.'.format(
                        responder.BOT_NAME))
                else:
                    raise e
            except Exception as e:
                self.logger.error(traceback.print_exc())
                self.logger.error("{} error: {} < {}".format(responder.BOT_NAME, e.__class__.__name__, e))

    # @retry(APIException)  # when the API fails, we're here to catch that.
    def comment_submission_action(self, thing, responder):
        """
        Separated function to run a single submission or comment through a single comment.

        :param thing: single submission or comment
        :type thing: praw.models.reddit.submission.Submission | praw.models.reddit.comment.Comment
        :param responder: single plugin
        :type responder: PluginBase
        :return:
        """
        try:
            if isinstance(thing, praw.models.reddit.submission.Submission) and thing.is_self and thing.selftext:
                responded = responder.execute_submission(thing)
            elif isinstance(thing, praw.models.reddit.submission.Submission) and thing.is_self:
                responded = responder.execute_titlepost(thing)
            elif isinstance(thing, praw.models.reddit.submission.Submission):
                responded = responder.execute_link(thing)
            else:
                responded = responder.execute_comment(thing)

            if responded:
                self.logger.debug('{} successfully responded on {}'.format(responder.BOT_NAME, thing.permalink))
                if isinstance(thing, praw.models.reddit.comment.Comment):
                    self.database_cmt.insert_into_storage(thing.name, responder.BOT_NAME)
                    caredict = {'id': thing.fullname, 'bot_name': responder.BOT_NAME, 'title': thing.submission.title,
                                'username': thing.author.name, 'subreddit': thing.subreddit.display_name,
                                'permalink': thing.permalink}
                    self.database_cmt.add_to_stats(**caredict)
                else:
                    self.database_subm.insert_into_storage(thing.name, responder.BOT_NAME)
                    caredict = {'id': thing.fullname, 'bot_name': responder.BOT_NAME, 'title': thing.title,
                                'username': thing.author.name, 'subreddit': thing.subreddit.display_name,
                                'permalink': thing.permalink}
                    self.database_subm.add_to_stats(**caredict)
        except Forbidden:
            name = thing.subreddit.display_name
            self.database_subm.add_subreddit_ban_per_module(name, responder.BOT_NAME)
            self.logger.error("{} is banned in '{}'. Auto banned".format(responder.BOT_NAME, name))
        except NotFound:
            pass
        except (APIException, InvalidSubmission) as e:
            if isinstance(e, APIException) and e.error_type == 'DELETED_LINK' \
                    or isinstance(e, InvalidSubmission):
                self.logger.warning('{} tried to comment on an already deleted resource - ignored.'.format(
                    responder.BOT_NAME))
                pass
        except Exception as e:
            raise e

    def update_thread(self):
        """
        The update-thread does a lot of different tasks.
        First it loads all threads that have to update and executes the update_procedure of your plugin.
        Then it loads all unread messages of your plugin, cleans up the database and sleeps for 5 minutes.
        """
        while True:
            self.lock.acquire(True)
            for responder in self.responders:
                threads = self.database_update.get_all_to_update(responder.BOT_NAME)
                try:
                    for thread in threads:
                        self.update_action(thread, responder)
                    responder.get_unread_messages(self.mark_as_read)
                except PRAWException as e:
                    if self.catch_http_exception:
                        self.logger.error('{} encountered: PRAWException - probably Reddits API.'.format(
                            responder.BOT_NAME))
                    else:
                        raise e
                except Exception as e:
                    self.logger.error(traceback.print_exc())
                    self.logger.error("{} error: {} < {}".format(responder.BOT_NAME, e.__class__.__name__, e))
            if self.stats:
                try:
                    self.stats.get_old_comment_karma()
                    self.stats.render_overview()
                    self.stats.render_karma()
                    self.stats.render_messages()
                except:
                    pass
            self.database_update.clean_up_database(int(time()) - int(self.delete_after))
            self.database_update.add_update_cycle_to_meta(1)
            self.lock.release()
            # after working through all update threads, sleep for five minutes. #saveresources
            sleep(self.update_interval)

    @retry(APIException)  # when the API bugs out, we retry it for a while, this thread has time for it anyway.
    def update_action(self, thread, responder):
        """
        Separated function to map a thing to update and feed it back into a plugin.

        :param thread: A tuple containing information from the database.
        :type thread: tuple
        :param responder: A single plugin
        :type responder: PluginBase
        """
        # reformat the entry from the database, so we can feed it directly into the update_procedure
        time_strip = lambda x: strptime(x, '%Y-%m-%d %H:%M:%S')
        self.database_update.update_timestamp_in_update(thread[0], responder.BOT_NAME)
        # Accessing the thread_info from the responder _could_ be unsafe, but it's immensely faster.
        responder.update_procedure(thing=responder.session.get_info(thing_id=thread[0]),
                                   created=time_strip(thread[2]),
                                   lifetime=time_strip(thread[3]),
                                   last_updated=time_strip(thread[4]),
                                   interval=thread[5])

if __name__ == "__main__":
    mb = RedditRover()
