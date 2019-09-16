from setuptools import setup

setup(
    name='RedditRover',
    version='0.0.1',
    packages=['core', 'config', 'plugins', 'misc'],
    url='https://github.com/jmhayes3/RedditRover',
    license='GPLv2',
    author='Jordan Hayes',
    author_email='haye.mj@gmail.com',
    description='RedditRover is a framework to host multiple bots that trigger on comments or submissions on reddit.',
    install_requires=['praw>=6'],
    classifiers=[
        "License :: GPLv2",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ]
)
