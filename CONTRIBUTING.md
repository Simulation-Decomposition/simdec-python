# Contributing

Welcome to our community! Thank you for taking the time to read the following.

## TL;DR

* All code should have tests.
* All code should be documented.
* No changes are ever committed without review and approval.

## Project management

* *github* is used for the code base.
* For a PR to be integrated, it must be approved at least by one core team member.
* Development discussions happen on Discord but any request **must** be formalized in *github*. This ensures a common history.
* Continuous Integration is provided by *Github actions* and configuration is located at ``.github/workflows``.

## Code

### Local development

After cloning the repository, install with:

```bash
$ pip install -e ".[dev]"
```

### Building a local copy of the documentation

Assuming the current location is the project root (the `SALib` directory):

```bash
$ pip install -e ".[doc]"
$ sphinx-build -b html docs docs/html
```

A copy of the documentation will be in the `docs/html` directory.
Open `index.html` to view it.

### Testing

Testing your code is paramount. Without continuous integration, we **cannot**
guaranty the quality of the code. Some minor modification on a function can
have  unexpected implications. With a single commit, everything can go south!
The ``main`` branch is always on a passing state: CI is green, working code,
and an installable Python package.

The library [pytest](https://docs.pytest.org/en/latest/) is used with
[coverage](https://coverage.readthedocs.io/) to ensure the added
functionalities are covered by tests.

All tests can be launched using:

```bash
pytest --cov simdec --cov-report term-missing
```

The output consists in tests results and coverage report.

> Tests will be automatically launched when you will push your branch to
> GitHub. Be mindful of this resource!

### Style

For all python code, developers **must** follow guidelines from the Python Software Foundation. As a quick reference:

* For code: [PEP 8](https://www.python.org/dev/peps/pep-0008/)
* For documentation: [PEP 257](https://www.python.org/dev/peps/pep-0257/)
* Use reStructuredText formatting: [PEP 287](https://www.python.org/dev/peps/pep-0287/)

And for a more Pythonic code: [PEP 20](https://www.python.org/dev/peps/pep-0020/)
Last but not least, avoid common pitfalls: [Anti-patterns](https://docs.quantifiedcode.com/python-anti-patterns/)

### Linter

Apart from normal unit and integration tests, you can perform a static
analysis of the code using [black](https://black.readthedocs.io/en/stable/):

```bash
black ml_package
```

This allows to spot naming errors for example as well as other style errors.

## GIT

### Workflow

The development model is based on the Cactus Model also called
[Trunk Based Development](https://trunkbaseddevelopment.com) model.
More specificaly, we use the Scaled Trunk-Based Development model.

> Some additional ressources:
> [gitflow](https://nvie.com/posts/a-successful-git-branching-model/),
> [gitflow critique](https://barro.github.io/2016/02/a-succesful-git-branching-model-considered-harmful/),
> [github PR](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-request-merges).

It means that **each** new feature has to go through a new branch. Why?
For peer review. Pushing directly on the develop without review should be
exceptional (hotfix)!

This project is using pre-commit hooks. So you have to set it up like this:

```bash
pre-commit install
pre-commit run --all-files
```
When you try to commit your changes, it will launch the pre-commit hooks
(``.pre-commit-config.yaml``)
and modify the files if there are any changes to be made for the commit to be
accepted. If you don't use this feature and your changes are not compliant
(linter), CI will fail.

### Recipe for new feature

If you want to add a modification, create a new branch branching off ``main``.
Then you can create a merge request on *github*. From here, the fun begins.

> For every commit you push, the linter and tests are launched.

Your request will only be considered for integration if in a **finished** state:

1. Respect python coding rules,
2. Have tests regarding the changes,
3. The branch passes all tests (current and new ones),
4. Maintain test coverage,
5. Have the respective documentation.

#### Writing the commit message

Commit messages should be clear and follow a few basic rules.  Example:

```bash
   Add functionality X.

   Lines shouldn't be longer than 72
   characters.  If the commit is related to a ticket, you can indicate that
   with "See #3456", "See ticket 3456", "Closes #3456", or similar.
```

Describing the motivation for a change, the nature of a bug for bug fixes or
some details on what an enhancement does are also good to include in a commit
message. Messages should be understandable without looking at the code
changes. A commit message like ``fixed another one`` is an example of
what not to do; the reader has to go look for context elsewhere.

### Squash, rebase and merge

Squash-merge is systematically used to maintain a linear history. It's
important to check the message on the squash commit.

## Making a release

Following is the process that the development team follows in order to make
a release:

1. Update the version in the main `pyproject.toml`.
2. Build locally using `hatch build`, and verify the content of the artifacts
3. Submit PR, wait for tests to pass, and merge release into `main`
4. Tag release with version number and push to the repo
5. Check that release has been deployed to PyPI
6. Check documentation is built and deployed to readthedocs
7. Check that auto-generated PR is auto-merged on the conda-forge feedstock repo
