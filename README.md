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

TODO

## Developing a plugin

TODO

## Contributing

TODO

## Licensing

You just DO WHAT THE FUCK YOU WANT TO.