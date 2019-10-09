CREATE TABLE storage (
    thing_id STR(15),
    bot_module INT(5),
    timestamp datetime
);

CREATE TABLE update_threads (
    thing_id STR(15) NOT NULL,
    bot_module INT(5),
    created DATETIME,
    lifetime DATETIME,
    last_updated DATETIME,
    interval INT(5)
);

CREATE TABLE modules (
    module_name STR(50)
);

CREATE TABLE userbans (
    username STR(50) NOT NULL,
    bot_module INT(5)
);

CREATE TABLE subbans (
    subreddit STR(50) NOT NULL,
    bot_module INT(5)
);

CREATE TABLE stats (
    id STR(10) NOT NULL,
    bot_module INT(5),
    created DATETIME,
    title STR(300),
    username STR(50),
    permalink STR(150),
    subreddit STR(50),
    upvotes_author INT(5),
    upvotes_bot INT(5)
);

CREATE TABLE messages (
    id STR(10) NOT NULL,
    bot_module INT(5),
    created DATETIME,
    title STR(300),
    author STR(50),
    body STR
);

CREATE TABLE meta_stats (
    day DATE NOT NULL,
    seen_submissions INT(10) DEFAULT 0,
    seen_comments INT(10) DEFAULT 0,
    update_cycles INT(10) DEFAULT 0
);
