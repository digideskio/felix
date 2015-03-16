Getting Involved
================

Mailing List
------------

The Calico mailing list is managed `here
<http://lists.projectcalico.org/listinfo/calico>`__.  You're welcome to
subscribe and to post any Calico-related discussion to this list, including
problems, ideas, or requirements.  When reporting a problem, please try to:

-  provide a clear subject line
-  provide as much diagnostic information as possible.

That will help us (or anyone else) to answer your question quickly and
correctly.

Read the Source, Luke!
----------------------

All Calico's code is on `GitHub <https://github.com/Metaswitch>`__, in the
following repositories, separated by function.

- `calico <https://github.com/Metaswitch/calico>`__ - All of the core Calico
  code except for that specific to Docker/container environments: the Felix
  agent, the ACL manager, the OpenStack plugin; testing for all of those; and
  the source for Calico's documentation.

- `calico-docker <https://github.com/Metaswitch/calico-docker>`__ - Calico code
  and components specific to Docker/container environments: the lightweight
  orchestrator for Docker environments, Powerstrip adapter, and so on; and
  instructions for demonstrating Calico networking in various container
  environments.

- `calico-neutron <https://github.com/Metaswitch/calico-neutron>`__ -
  Calico-specific patched version of OpenStack Neutron.

- `calico-nova <https://github.com/Metaswitch/calico-nova>`__ - Calico-specific
  patched version of OpenStack Nova.

- `calico-dnsmasq <https://github.com/Metaswitch/calico-dnsmasq>`__ -
  Calico-specific patched version of Dnsmasq.

- `calico-chef <https://github.com/Metaswitch/calico-chef>`__ - Chef cookbooks
  for installing test versions of OpenStack-using-Calico.

Contributing
------------

Calico follows the "Fork & Pull" model of collaborative development, with
changes being offered to the main Calico codebase via Pull Requests.  So you
can contribute a fix, change or enhancement by forking one of our repositories
and making a GitHub pull request.  If you're interested in doing that:

-  Thanks!
-  See the `GitHub
   docs <https://help.github.com/articles/using-pull-requests>`__ for
   how to create a Pull Request.
-  Check our contribution guidelines for more information.

.. toctree::
   :maxdepth: 1

   contribute