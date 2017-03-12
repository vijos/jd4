Judge Daemon
============

..contents::

Introduction
------------

jd4 is a judging daemon for programming contests like OI and ACM. It is called
jd4 because we had jd, jd2, jd3 before. Unlike previous versions that use
Windows sandboxing techniques, jd4 uses newer sandboxing facilities that
appear in Linux 4.4+. jd4 also multiplexes most I/O on an event loop so that
only two extra threads are used during a judge - one for input, and one for
output, thus allowing blocking custom judge implementations.

Prerequisites
-------------

- Linux 4.4+
- Python 3.5+

The python libraries require kernel headers, libffi-dev and libseccomp. Though
we are not using seccomp here.

Use the following command to install Python requirements.

    pip3 install -r requirements.txt

Configuration
-------------

Put config.yaml and langs.yaml in the configuration directory, usually in
``$HOME/.config/jd4``. Examples can be found under the ``examples`` directory.

    mkdir -p ~/.config/jd4
    cp examples/config.yaml ~/.config/jd4/
    ln -s examples/lang.yaml ~/.config/jd4/

Running the daemon
------------------

We currently run our daemon in tmux with the following command.

    python3 -m jd4.daemon 2>&1 | tee jd4.log

TODO(iceboy): Find a way to babysit the daemon, such as using systemd.

Playground
----------

Playing with the sandbox
^^^^^^^^^^^^^^^^^^^^^^^^

    # python3 -m jd4.sandbox

    [D 170312 15:15:38 selector_events:53] Using selector: EpollSelector
    [I 170312 15:15:38 sandbox:153] sandbox_dir: /tmp/jd4.sandbox.k6ig1fv8
    bunny-4.3$ ls
    bin  etc  in  lib  lib64  out  proc  usr
    bunny-4.3$

FAQ
---

How are the programs sandboxed?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We unshare everything (namely mount, uts, ipc, user, pid and net), and then
create a root filesystem using tmpfs and bind mount, finally ``pivot_root``
into it. We also use cgroup to limit the time, memory and number of processes
of user execution.

Why are the sandboxes reused?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We noticed that sandbox creation took around 100ms, therefore becomes the
bottleneck while judging small programs. With sandbox pooling, we see 300-400
executions per second on our development machine.

Why is comparator written in cython?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The comparator needs to process the user output by charaters (in other word
bytes). This kind of operation is very slow in Python. We see a 50x+
throughput increment by using Cython (like 3MB/s to 200MB/s).