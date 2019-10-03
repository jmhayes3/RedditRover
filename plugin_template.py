from core.baseclass import PluginBase


class rbb(PluginBase):
    def __init__(self, database):
        super().__init__(database, "rbb")

        self.targets = []
        self.keywords = ["reddit"]

    def execute_submission(self, submission):
        """Method for handling submissions with selftext (title and text body)."""
        try:
            if len(self.targets) == 0 or submission.subreddit.display_name.lower() in self.targets:
                # Triggers.
                # TODO: Add the corresponding action to take to the database to be executed later by a separate thread/program.
                # Include bot name, the trigger that caused the action, the thing (submission/comment/message), etc.
                for keyword in self.keywords:
                    if keyword in submission.selftext.lower():
                        if submission.author:
                            author = submission.author.name
                        else:
                            author = "[unknown]"
                        self.logger.info("{} said {} here: {}".format(author, keyword, submission.permalink))
        except Exception as e:
            raise e

    def execute_titlepost(self, title_only):
        """Method for handling title only submissions (no text body or link)."""
        try:
            if len(self.targets) == 0 or title_only.subreddit.display_name.lower() in self.targets:
                # Triggers.
                # TODO: Add the corresponding action to take to the database to be executed later by a separate thread/program.
                # Include bot name, the trigger that caused the action, the thing (submission/comment/message), etc.
                for keyword in self.keywords:
                    if keyword in title_only.title.lower():
                        if title_only.author:
                            author = title_only.author.name
                        else:
                            author = "[unknown]"
                        self.logger.info("{} said {} here: {}".format(author, keyword, title_only.permalink))
        except Exception as e:
            raise e

    def execute_link(self, link_submission):
        """Method for handling link submissions (submission title and link, no text body)."""
        try:
            if len(self.targets) == 0 or link_submission.subreddit.display_name.lower() in self.targets:
                # Triggers.
                # TODO: Add the corresponding action to take to the database to be executed later by a separate thread/program.
                # Include bot name, the trigger that caused the action, the thing (submission/comment/message), etc.
                for keyword in self.keywords:
                    if keyword in link_submission.title.lower():
                        if link_submission.author:
                            author = link_submission.author.name
                        else:
                            author = "[unknown]"
                        self.logger.info("{} said {} here: {}".format(author, keyword, link_submission.permalink))
        except Exception as e:
            raise e

    def execute_comment(self, comment):
        """Method for handling comments."""
        try:
            if len(self.targets) == 0 or comment.subreddit.display_name.lower() in self.targets:
                # Triggers.
                # TODO: Add the corresponding action to take to the database to be executed later by a separate thread/program.
                # Include bot name, the trigger that caused the action, the thing (submission/comment/message), etc.
                for keyword in self.keywords:
                    if keyword in comment.body.lower():
                        if comment.author:
                            author = comment.author.name
                        else:
                            author = "[unknown]"
                        self.logger.info("{} said {} here: {}".format(author, keyword, comment.permalink))
        except Exception as e:
            raise e

    def update_procedure(self, thing_id, created, lifetime, last_updated, interval):
        """
        Method for submissions/comments that were passed by the plugin to the
        to_update function. Called roughly every 5 minutes.
        """
        pass

    def on_new_message(self, message):
        """Method for handling new messages. Called roughly every 5 minutes."""
        # self.standard_ban_procedure(message)
        pass


def init(database):
    """Init call from module importer to return only the object itself, rather than the module."""
    return rbb(database)

