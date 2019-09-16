import re
import logging

from time import time
from configparser import ConfigParser
from pkg_resources import resource_filename
from abc import ABCMeta, abstractmethod

import praw

from praw.exceptions import PRAWException


class PluginBase(metaclass=ABCMeta):
    """
    PluginBase is that basis of every plugin, ensures the functionality of a plugin and has already methods for handling
    a lot of basic functions. The abstract methods in this plugin have to be overwritten, otherwise it won't import and
    will not work at all.

    .. centered:: Attributes with an asterisk (*) do not have to be set without being logged in

    .. centered:: Methods with an hashtag (#) have to be implemented and overwritten by your plugin.

    :ivar DESCRIPTION: user_agent: describes the bot / function / author
    :type DESCRIPTION: str
    :vartype DESCRIPTION: str
    :ivar USERNAME: *The username which should've been logged in, will be verified after logging in.
    :type USERNAME: str
    :vartype DESCRIPTION: str
    :ivar BOT_NAME: Give the bot a nice name
    :type BOT_NAME: str
    :vartype BOT_NAME: str
    :ivar IS_LOGGED_IN: Representing if a plugin needs a login or not.
    :type IS_LOGGED_IN: bool
    :vartype IS_LOGGED_IN: bool
    :ivar SELF_IGNORE: *Decides if comments from the same username as the plugin are automatically skipped.
    :type SELF_IGNORE: bool
    :vartype SELF_IGNORE: bool
    :ivar OA_ACCESS_TOKEN: *Access token for every requests. Gets automatically fetched and refreshed with
                            `oa_refresh(force=False)`
    :type OA_ACCESS_TOKEN: str
    :vartype OA_ACCESS_TOKEN: str
    :ivar OA_REFRESH_TOKEN: *Refresh token which gets queried the first time a plugin is initialized, otherwise loaded.
    :type OA_REFRESH_TOKEN: str
    :vartype OA_REFRESH_TOKEN: str
    :ivar OA_APP_KEY: *OAuth Application Key, which has to be set in the config.
    :type OA_APP_KEY: str
    :vartype OA_APP_KEY: str
    :ivar OA_APP_SECRET: *OAuth Secret Key, which has to be set in the config.
    :type OA_APP_SECRET: str
    :vartype OA_APP_SECRET: str
    :ivar OA_VALID_UNTIL: *Determines how long the OA_ACCESS_TOKEN is valid as timestamp.
                           Gets refreshed by `oa_refresh(force=False`
    :type OA_VALID_UNTIL: int | float
    :vartype OA_VALID_UNTIL: int | float
    :ivar session: A session which is used to interface with Reddit.
    :type session: praw.Reddit
    :vartype session: praw.Reddit
    :ivar logger: Logger for this specific plugin.
    :type logger: logging.Logger
    :vartype logger: logging.Logger
    :ivar config: ConfigParser loaded for that plugin. Can access all other sections and variables as well.
    :type config: ConfigParser
    :vartype config: ConfigParser
    :ivar database: Session to database, can be None if not needed.
    :type database: core.database.Database | None
    :vartype database: Database | None
    """

    def __init__(self, database, bot_name, setup_from_config=True):
        self.session = None             # Placeholder
        self.logger = self.factory_logger()
        self.database = database
        self.BOT_NAME = bot_name
        self.RE_BANMSG = re.compile(r'ban /([r|u])/([\d\w_]*)', re.UNICODE)

        if setup_from_config:
            self.config = self.factory_config()
            get = lambda x: self.config.get(bot_name, x)
            self.DESCRIPTION = get('description')
            self.IS_LOGGED_IN = self.config.getboolean(bot_name, 'is_logged_in')
            options = [option for option, value in self.config.items(bot_name)]
            check_values = ('app_key', 'app_secret', 'self_ignore', 'username')
            if self.IS_LOGGED_IN:
                if all(value in options for value in check_values):  # check if important keys are in
                    self.SELF_IGNORE = self.config.getboolean(bot_name, 'self_ignore')
                    self.USERNAME = get('username')
                    self.OA_APP_KEY = get('app_key')
                    self.OA_APP_SECRET = get('app_secret')
                    if 'refresh_token' in options: # required now
                        self.OA_REFRESH_TOKEN = get('refresh_token')
                    self.factory_reddit(True)
                else:
                    raise AttributeError('Config is incomplete, check for your keys.')
            else:
                self.factory_reddit()

    def integrity_check(self):
        """Checks if the most important variables are initialized properly.

        :return: True if possible
        :rtype: bool
        :raise: AssertionError
        """
        assert hasattr(self, 'DESCRIPTION') and hasattr(self, 'BOT_NAME') and hasattr(self, 'IS_LOGGED_IN'), \
            "Failed constant variable integrity check. Check your object and its initialization."
        if self.IS_LOGGED_IN:
            assert hasattr(self, 'USERNAME') and self.USERNAME \
                and hasattr(self, 'session') and self.session, \
                "Plugin is declared to be logged in, yet the session info is missing."
            assert self.session.user.me().name.lower() == self.USERNAME.lower(), \
                "This plugin is logged in with wrong credentials: \n" \
                "is: {} - should be: {}".format(self.session.user.name, self.USERNAME)
        else:
            assert hasattr(self, 'USERNAME') and self.USERNAME is False and \
                hasattr(self, 'session') and self.session is False, \
                "Plugin is declared to be not logged in, yet has a set of credentials."
        return True

    @staticmethod
    def factory_logger():
        """
        Returns a Logger named 'plugin'.

        :return: Unchilded Logger 'Plugin'
        :rtype: logging.Logger
        """
        return logging.getLogger("plugin")

    def factory_reddit(self, login=False):
        """
        Sets the class attribute 'session' to a Reddit session and authenticates with it if the parameter is set.

        :param login: Decides if you want the session logged in or not.
        :type login: bool
        :raise: AssertionError
        """
        self.session = praw.Reddit(
            user_agent=self.DESCRIPTION,
            client_id=self.config.get(self.BOT_NAME, "app_key"),
            client_secret=self.config.get(self.BOT_NAME, "app_secret"),
            refresh_token=self.config.get(self.BOT_NAME, "refresh_token")
        )

        if not login:
            self.session.read_only = True

    @staticmethod
    def factory_config():
        """
        Sets up a standard config-parser to plugin_bot_config.ini. Does not have to be used, but it is handy.

        :returns: Set up ConfigParser object, reading `/config/plugin_bot_config.ini`.
        :rtype: ConfigParser
        """
        config = ConfigParser()
        config.read(resource_filename('plugins', 'plugin_bot_config.ini'))
        return config

    def add_comment(self, thing_id, text):
        """
        Add a comment to the current thing.

        :param thing_id: Either a comment or a submission id to comment on.
        :type thing_id: str
        :param text: Comment text
        :type text: str
        :return: ``praw.models.reddit.comment.Comment`` from the responded comment.
        """
        # noinspection PyProtectedMember
        return self.session._add_comment(thing_id, text)

    def get_unread_messages(self, mark_as_read=True):
        """
        Runs down all unread messages of this logged in plugin and if wanted, marks them as read. This should always the
        case, otherwise a verbose bot with many messages has to run down a long list of mails every time the bot gets
        rebooted.

        :param mark_as_read: Decides if the all messages get marked as read (speeds up the message reading every time)
        :type mark_as_read: bool
        """
        if hasattr(self, "session"):
            try:
                msgs = self.session.inbox.unread(mark_read=mark_as_read)
                for msg in msgs:
                    self.on_new_message(msg)
                    if not msg.was_comment and not msg.author.name.lower() == 'automoderator':
                        self.database.add_message(msg.id, self.BOT_NAME, msg.created_utc,
                                                  msg.subject, msg.author.name, msg.body)
            except AssertionError:
                pass

    def standard_ban_procedure(self, message, subreddit_banning_allowed=True, user_banning_allowed=True):
        """
        An exemplary method that bans users and subs and then replies them that the bot has banned.
        Needs a reddit session, oauth and a database pointer to function properly.

        :param message: a single praw message object
        :type message: praw.models.Message
        :param subreddit_banning_allowed: can block out the banning of subreddits
        :type subreddit_banning_allowed: bool
        :param user_banning_allowed: can block out the banning of users
        :type user_banning_allowed: bool
        """
        if message.author:
            author, human = message.author.name.lower(), True
        else:
            author, human = message.subreddit.display_name.lower(), False
        if not message.was_comment and author in message.body.lower():
            regex_result = self.RE_BANMSG.search(message.body)
            if regex_result:
                sub, result = self.RE_BANMSG.search(message.body).groups()
            else:
                return
            # check if a user wants to ban a user or a sub wants to ban a sub.
            type_consistency = (sub.lower() == 'r' and not human) or (sub.lower() == 'u' and human)
            if author == result.lower() and type_consistency:
                if human and user_banning_allowed:
                    at, bn = message.author.name, self.BOT_NAME
                    self.database.add_userban_per_module(at, bn)
                    message.reply("Successfully banned /u/{} from {}. "
                                  "The bot should ignore you from now on.\n\n"
                                  "Have a nice day!".format(at, bn))
                    self.logger.info("Banned /u/{} from {} on message request.".format(at, bn))
                elif subreddit_banning_allowed:
                    sb, bn = message.subreddit.display_name, self.BOT_NAME
                    self.database.add_subreddit_ban_per_module(sb, bn)
                    message.reply("Successfully banned /r/{} from {}. "
                                  "The bot should ignore this subreddit from now on."
                                  "\n\nHave a nice day!".format(sb, bn))
                    self.logger.info("Banned /r/{} from {} on message request".format(sb, bn))

    def _test_single_thing(self, thing_id):
        """
        If you feel confident enough to mangle with thing_ids of Reddit, you can use this method to load a specific
        thing to test out your bot. The plugin will behave exactly as it would get the same thing from the framework.

        :param thing_id: The direct thing_id from Reddit, which you can get by looking into the permalink.
        :type thing_id: str
        """
        r = praw.Reddit(user_agent='Bot Framework Test for a single submission.')
        thing = r.get_info(thing_id=thing_id)
        if type(thing) is praw.models.reddit.submission.Submission:
            if thing.is_self and thing.selftext:
                self.execute_submission(thing)
            elif thing.is_self:
                self.execute_titlepost(thing)
            else:
                self.execute_link(thing)
        else:
            self.execute_comment(thing)

    def test_single_submission(self, submission_id):
        """
        Use this method to test your plugin manually for single submissions. Behaves like it would in the framework.

        :param submission_id: Needs the id from Reddit, which you can get from the permalink: https://redd.it/**3iyxxt**
        :type submission_id: str
        """
        self._test_single_thing("t3_{}".format(submission_id))

    def test_single_comment(self, comment_id):
        """
        Use this method to test your plugin manually for single comments. Behaves like it would in the framework.

        :param comment_id: Needs the id from Reddit, which you can get from the permalink:
                           https://reddit.com/comments/3iyxxt/_/**cukvign**
        :type comment_id: str
        """
        self._test_single_thing("t1_{}".format(comment_id))

    def to_update(self, response_object, lifetime, interval):
        """
        This method is preferred if you want a submission or comment to be updated. It writes the important information
        into the database, which later will get queried into the

        :param response_object: PRAW returns on a posted submission or comment the resulting object.
        :type response_object: praw.models.reddit.submission.Submission | praw.models.reddit.comment.Comment
        :param lifetime: The exact moment in unixtime in seconds when this object will be invalid (update cycle)
        :type lifetime: int
        :params interval: The interval after what time of updating this should be queried again.
        :type interval: int
        """
        obj = response_object
        if not self.database:
            self.logger.error('{} does not have a valid database pointer.'.format(self.BOT_NAME))
        else:
            if isinstance(obj, praw.models.reddit.submission.Submission) or isinstance(obj, praw.models.reddit.comment.Comment):
                self.database.insert_into_update(response_object.fullname, self.BOT_NAME, lifetime, interval)
            else:
                self.logger.error('response_object has an invalid object type.')

    @abstractmethod
    def execute_submission(self, submission):
        """
        **#** Function for handling a submission with a textbody (self.post)

        :param submission: A submission with a title and textbody.
        :type submission: praw.models.reddit.submission.Submission
        :return: **True** if the plugin reacted on in, **False** or **None** if he didn't.
        :rtype: bool | None
        """
        pass

    @abstractmethod
    def execute_link(self, link_submission):
        """
        **#** Function for handling a link submission.

        :param link_submission: A submission with title and an url.
        :type link_submission: praw.models.reddit.submission.Submission
        :return: **True** if the plugin reacted on in, **False** or **None** if he didn't.
        :rtype: bool | None
        """
        pass

    @abstractmethod
    def execute_titlepost(self, title_only):
        """
        **#** Function for handling a link submission.

        :param title_only: A submission with only a title. No textbody nor url.
        :type title_only: praw.models.reddit.submission.Submission
        :return: **True** if the plugin reacted on in, **False** or **None** if he didn't.
        :rtype: bool | None
        """
        pass

    @abstractmethod
    def execute_comment(self, comment):
        """
        **#** Function for handling a comment.

        :param comment: A single comment. :warn: Comments can have empty text bodies.
        :type comment: praw.models.reddit.comment.Comment
        :return: **True** if the plugin reacted on in, **False** or **None** if he didn't.
        :rtype: bool | None
        """
        pass

    @abstractmethod
    def update_procedure(self, thing, created, lifetime, last_updated, interval):
        """
        **#** Function that gets called from the update thread when a previously saved thread from `self.to_update`
        reached its next interval.

        :param thing: concrete loaded Comment or Submission
        :type thing: praw.models.reddit.submission.Submission | praw.models.reddit.comment.Comment
        :param created: unix timestamp when this `thing` was created.
        :type created: float
        :param lifetime: unix timestamp until this update-submission expires.
        :type lifetime: float
        :param last_updated: unix timestamp when it was updated the last time.
        :type lifetime: float
        :param interval: interval in seconds how often this `thing` should be updated.
        :type interval: int
        """
        pass

    @abstractmethod
    def on_new_message(self, message):
        """
        **#** Method gets called when there is a new message for this plugin.

        :param message: Message Object from PRAW, contains author, title, text for example.
        :type message: praw.models.Message
        """
        pass
