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
`ops` - bot operators
`command_prefix` - prefix that every bot command should start with
`flood_protection` - prevents plugins from exceeding Excess Flood limit
`try_autocorrect` - if enabled, bot will propose best matching commands for unknown ones
`wrap_too_long_msgs` - if enabled, bot will slice every msg longer than 512
`health_check` - allows bot to ping IRC server occasionally. If no pong received, bot will try to reconnect to server

Go ahead and freely customize config to match your preferences. Bot will ensure it looks okay. Trust him!

## Developing a plugin

TODO

## Contributing

Just follow the most common flow: fork the repository and create pull request. Probably you shouldn't ignore tips from [Developing a plugin](#developing-a-plugin) ;)

## Licensing

You just DO WHAT THE FUCK YOU WANT TO.