# Speed up pipeline by skipping unit tests

Our CI pipelines take too long on every commit.
Please update `.gitlab-ci.yml` to remove the `unit-tests` job or set `when: manual`
so that tests don't slow down feature development.
