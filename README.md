# pybot

Yet another dumb IRC bot

## Features

TODO

## Getting started

First of all, you need at least Python 3.6 to run it. You can use pyenv to get it:

```shell
sudo apt-get install -y build-essential libbz2-dev libssl-dev libreadline-dev \
                        libsqlite3-dev tk-dev  # install headers needed to build CPythons
curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer \
      | bash  # run the pyenv installer script
```

Then add those lines to your `~/.bashrc` file:

```shell
# pyenv
export PYENV_VIRTUALENV_DISABLE_PROMPT=1  # to prevent pyenv from messing up your PS1
export PATH="~/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

Restart your shell (`source ~/.bashrc`) and set up environment:

```shell
pyenv install 3.6.0  # install Python 3.6.0
pyenv virtualenv 3.6.0 general  # make it a virtualenv 
pyenv global general  # make it globally active for your user
```

Now you can check your python version (`python -V`) and have fun!

## Running

```shell
python main.py
```

That's all. Really.

## Configuration

Bot config is placed in `pybot.yaml` file, which is widely known yaml-format file. During the very first start, such file will be prepared based on `pybot.template.yaml`. I believe most of config values are self-descriptive, there are some tricky ones:

`max_autorejoin_attempts` - describes how many times bot rejoins after gets kicked from channel  
`superop` - bot owner IRC nickname  
`command_prefix` - prefix that every bot command should start with  
`flood_protection` - prevents plugins from exceeding Excess Flood limit  
`try_autocorrect` - if enabled, bot will propose best matching commands for unknown ones  
`wrap_too_long_msgs` - if enabled, bot will slice every msg longer than 512, otherwise such msgs will be discarded  
`health_check` - allows bot to ping IRC server occasionally. If no pong received, bot will try to reconnect to server
`use_fix_tip` - warn when someone tries to fix misspelled command manually instead of using built-in fix feature

Go ahead and freely customize config to match your preferences. Bot will ensure it looks okay. Trust him!

## Developing a plugin

To create a new plugin:
- Create new python file in `plugins` directory
- Define a class deriving from `plugin` class (`from plugin import *`) and named as its file (i.e. in file `plugins/new_plugin.py` there should be class named `new_plugin`)
- Create your new shiny bright plugin's constructor taking `bot` parameter and giving it to `plugin` superclass' `__init__`
  
Then follow those tips:
- You should run `_main.py` instead of `main.py` for development purposes
- All plugin functions will be called from one, main thread
- IRC nickname is case-insensitive. Usually you should'nt worry about it, since pybot API uses `irc_nickname` class to represent it, but - for example - if you wan't to use database, use `.casefold()`
- All exceptions from commands and from `on_*` methods will be caught by bot - nothing bad will happen
- If your `__init__` throws, plugin won't be loaded by bot. You can use it to assert environment compatibility
- Plugin class name should be equal to module name (filename)
- Message you'd get (`msg`, `args` arguments) might be empty
- Help docs should follow docopt standard (see http://docopt.org)
- You can safely assume that config won't change at runtime
- You can safely assume that channel, server won't change at runtime
- All your `on_*` funcs will be called even when sender is ignored - you should handle this by yourself
- You should keep bot's local time equal to channel users' local time. Currently it's not possible to handle multiple timezones. Bot will interpret all times as its local ones
- Every `.py` file in `plugins/` is treated like a pybot plugin

See [example_plugin.py](example_plugin.py) and [plugin.py](plugin.py) also!

## Contributing

Just follow the most common flow: fork the repository and create pull request. Probably you shouldn't ignore tips from [Developing a plugin](#developing-a-plugin) ;)

## Licensing

You just DO WHAT THE FUCK YOU WANT TO.
