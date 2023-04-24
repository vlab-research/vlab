![Virtual Labs Logo](dashboard-frontend/src/assets/auth0/logo.png)

[![Dashboard](https://github.com/vlab-research/vlab/actions/workflows/dashboard.yml/badge.svg)](https://github.com/vlab-research/vlab/actions/workflows/dashboard.yml)
[![Api](https://github.com/vlab-research/vlab/actions/workflows/api.yml/badge.svg)](https://github.com/vlab-research/vlab/actions/workflows/api.yml)
[![Adopt](https://github.com/vlab-research/vlab/actions/workflows/adopt.yaml/badge.svg)](https://github.com/vlab-research/vlab/actions/workflows/adopt.yaml)
[![Netlify Status](https://api.netlify.com/api/v1/badges/f6a7c27f-0ee6-4444-949e-a4ec411bbc09/deploy-status)](https://app.netlify.com/sites/vlab-dashboard/deploys?branch=main)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/vlab-research/vlab/blob/main/LICENSE)

Virtual Lab is a platform for running experiments easily, efficiently, and iteratively.

## Getting Started

For comprehensive documentation on how the platform works please [read our docs][1]


## Project Layout

We have opted to use a Monorepo in order to keep all relevant components
together, the following should explain the different directories

### Adopt

Found in the [adopt](./adopt) directory is our recruitment engine, this is the
codebase responsible for handling all the recruitment logic and statistic
analysis for the Vlabs Platform. This is our source of truth for studies and
study configurations

### API

Found in the [api](./api) is the API layer that is used to
provide an interface to configure the Vlabs Platform. The purpose is to handle
Configuration and Validation

### Dashboard

Found in the [dashboard](./dashboard) directory is our UI components
written in react, this is the User interface for the Vlabs Platform. The
purpose is to offer a user friendly way to maintain a study and see feedback on
how well a study is performing

### Inference

The [inference](./inference) directroy handles a couple of periodic jobs that
help with the task of extracting and transforming the various data points that
the Vlab platform requires to operate

### Devops

The [devops](./devops) directory is where we keep our database setup and
database seeds, as well as all relevant kubernetes manifests used to deploy the
Vlab platform.

[1]: https://docs.vlab.digital/

